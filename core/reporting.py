"""Operational measures with explicit populations, periods and payment units."""
from datetime import timedelta
from django.db.models import Count, Sum, Avg, Min
from django.db.models.functions import TruncDate
from django.urls import reverse
from django.utils import timezone
from .models import (User, AccountActivity, Job, Assignment, Payment, Dispute,
                     SupportTicket, TicketReply, TicketFeedback, Invitation, EmailDelivery)


def daily_counts(query, field, start, end):
    rows=(query.filter(**{f'{field}__date__gte':start,f'{field}__date__lte':end})
          .order_by().annotate(day=TruncDate(field)).values('day').annotate(count=Count('pk')))
    return {row['day']:row['count'] for row in rows}


def report_data(role, days=30):
    now=timezone.now()
    today=timezone.localdate(now)
    start=today-timedelta(days=days-1)
    previous=start-timedelta(days=days)
    members=User.objects.filter(staff_access__isnull=True,is_superuser=False)
    member_ids=members.values('pk')
    total=members.count()
    activity=AccountActivity.objects.filter(user_id__in=member_ids)
    active_today=activity.filter(day=today).count()
    active_period=activity.filter(day__gte=start,day__lte=today).values('user_id').distinct().count()
    online=activity.filter(last_seen__gte=now-timedelta(minutes=5)).values('user_id').distinct().count()
    first_activity=activity.aggregate(first=Min('day'))['first']
    jobs=Job.objects.filter(demo=False)
    assignments=Assignment.objects.filter(job__demo=False)
    payments=Payment.objects.filter(assignment__job__demo=False)

    def metric(label,query,field,unit=''):
        current=query.filter(**{f'{field}__date__gte':start,f'{field}__date__lte':today}).count()
        prior=query.filter(**{f'{field}__date__gte':previous,f'{field}__date__lt':start}).count()
        delta=current-prior
        return {'label':label,'value':current,'note':f'{delta:+d} vs previous {days} days','unit':unit}

    def queue(label,query,url):
        return {'label':label,'value':query.count(),'url':reverse(url)}

    common=[{'label':'Total members','value':total,'note':'Registered members · staff excluded'},
            {'label':'New accounts today','value':members.filter(date_joined__date=today).count(),'note':today.strftime('%d %b %Y')},
            {'label':'Active today','value':active_today,'note':f'{active_today} of {total} members used Push today'},
            {'label':'Recently online','value':online,'note':'Signed-in page use in the last 5 minutes'}]
    if role in {'owner','admin'}:
        series_sources=[('New members',members,'date_joined'),('Jobs completed',payments,'created_at')]
        metrics=[metric('New members',members,'date_joined'),metric('Jobs posted',jobs,'created_at'),
                 metric('Assignments created',assignments,'created_at'),metric('Jobs completed',payments,'created_at')]
        queues=[queue('Listings awaiting review',jobs.filter(moderation_status='review'),'moderation'),
                queue('Open disputes',Dispute.objects.exclude(status='resolved'),'moderation'),
                queue('Unanswered tickets',SupportTicket.objects.filter(status='open'),'operations_tickets'),
                queue('Failed emails in this period',EmailDelivery.objects.filter(status='failed',created_at__date__gte=start),'operations_email')]
        chart_title='Member growth & completed work'
    elif role == 'moderator':
        series_sources=[('Disputes opened',Dispute.objects.all(),'created_at'),('Disputes resolved',Dispute.objects.filter(status='resolved'),'resolved_at')]
        metrics=[metric('Disputes opened',Dispute.objects.all(),'created_at'),
                 metric('Disputes resolved',Dispute.objects.filter(status='resolved'),'resolved_at'),
                 {'label':'Under review','value':Dispute.objects.filter(status='under_review').count(),'note':'Current dispute queue'},
                 {'label':'Listings awaiting review','value':jobs.filter(moderation_status='review').count(),'note':'Current listing queue'}]
        queues=[queue('Disputes needing a decision',Dispute.objects.exclude(status='resolved'),'moderation'),
                queue('Listings awaiting review',jobs.filter(moderation_status='review'),'moderation'),
                queue('Unclaimed tester invitations',Invitation.objects.filter(used_at__isnull=True,revoked_at__isnull=True,expires_at__gt=now),'staff_invitations')]
        chart_title='Dispute activity'
    else:
        tickets=SupportTicket.objects.all()
        replies=TicketReply.objects.filter(internal=False,author__staff_access__status='approved')
        series_sources=[('Tickets opened',tickets,'created_at'),('Staff replies',replies,'created_at')]
        metrics=[metric('Tickets opened',tickets,'created_at'),metric('Staff replies',replies,'created_at'),
                 {'label':'Waiting for member','value':tickets.filter(status='waiting_user').count(),'note':'Current ticket queue'},
                 {'label':'Unassigned tickets','value':tickets.filter(assigned_to__isnull=True).exclude(status__in=['resolved','closed']).count(),'note':'Ready for a team member'}]
        queues=[queue('Urgent unresolved tickets',tickets.filter(priority='urgent').exclude(status__in=['resolved','closed']),'operations_tickets'),
                queue('Open over 48 hours',tickets.filter(created_at__lt=now-timedelta(hours=48)).exclude(status__in=['resolved','closed']),'operations_tickets'),
                queue('Unassigned tickets',tickets.filter(assigned_to__isnull=True).exclude(status__in=['resolved','closed']),'operations_tickets')]
        chart_title='Support demand & responses'

    dates=[start+timedelta(days=i) for i in range(days)]
    series=[]
    for label,query,field in series_sources:
        counts=daily_counts(query,field,start,today)
        series.append({'label':label,'values':[counts.get(day,0) for day in dates]})
    peak=max(2,*(value for group in series for value in group['values']))
    peak=((peak+1)//2)*2
    # SVG coordinates are generated from trusted numeric aggregates, never user input.
    for group in series:
        coords=[(48+i*704/(days-1),224-value*188/peak) for i,value in enumerate(group['values'])]
        group['path']=' '.join(f'{"M" if i==0 else "L"}{x:.1f},{y:.1f}' for i,(x,y) in enumerate(coords))
        group['area']=group['path']+' L752,224 L48,224 Z'
        group['total']=sum(group['values'])
    rows=[{'day':day,'first':series[0]['values'][i],'second':series[1]['values'][i]} for i,day in enumerate(dates)]
    finance=None
    if role in {'owner','admin'}:
        period_payments=payments.filter(created_at__date__gte=start,created_at__date__lte=today)
        finance={'verified_testnet':period_payments.filter(simulated=False).aggregate(total=Sum('amount'))['total'] or 0,
                 'simulated':period_payments.filter(simulated=True).aggregate(total=Sum('amount'))['total'] or 0}
    feedback=TicketFeedback.objects.filter(created_at__date__gte=start,created_at__date__lte=today)
    feedback_total=feedback.count()
    feedback_good=feedback.filter(rating__gte=4).count()
    feedback_average=feedback.aggregate(value=Avg('rating'))['value']
    pipeline=[('Open',jobs.filter(status='open').count()),('Assigned',jobs.filter(status='assigned').count()),
              ('Completed',jobs.filter(status='completed').count()),('Closed',jobs.filter(status='closed').count())]
    job_total=sum(value for _,value in pipeline)
    report={
        'days':days,'start':start,'today':today,'updated_at':now,'common':common,'metrics':metrics,
        'series':series,'rows':rows,'chart_title':chart_title,'peak':peak,'half_peak':peak//2,
        'midpoint':dates[len(dates)//2],'queues':queues,'finance':finance,
        'active_period':active_period,'member_total':total,
        'active_percent':round(active_period*100/total) if total else 0,
        'first_activity':first_activity,
        'pipeline':[{'label':label,'value':value,'percent':round(value*100/job_total) if job_total else 0} for label,value in pipeline],
        'job_total':job_total,'feedback_total':feedback_total,'feedback_good':feedback_good,
        'feedback_average':round(feedback_average,1) if feedback_average is not None else None,
        'feedback_percent':round(feedback_good*100/feedback_total) if feedback_total else None,
    }
    return report
