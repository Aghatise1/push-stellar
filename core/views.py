import hashlib
import hmac
import json
import secrets
import os
from urllib.parse import quote
from datetime import timedelta
from functools import wraps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.hashers import make_password
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, PasswordResetView
from django.core import signing
from django.core.mail import send_mail
from django.utils.crypto import salted_hmac
from django.db import connection, transaction, IntegrityError
from django.db.models import Q, F, Sum, Max
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseForbidden, Http404, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_GET, require_POST
from django.views.decorators.cache import never_cache
from .models import User, EmailVerificationCode, PendingRegistration, Job, Application, Assignment, Submission, Event, Payment, RateBucket, Message, Dispute, AccountSanction, Notification, WaitlistApplication, Invitation
from .forms import Registration, LoginForm, RecoveryForm, VerificationCodeForm, ProfileForm, JobForm, ApplicationForm, SubmissionForm, ActionForm, MessageForm, WalletRequestForm, DisputeResolutionForm, SanctionForm, WaitlistForm, InvitationCodeForm, StaffInvitationForm
from .stellar import StellarVerificationError, account_balances, assignment_memo, payment_uri, verify_payment, valid_account_id
from .invitations import consume_invitation, current_invitation, hash_invitation_code, remember_invitation

TERMS_VERSION='2026-09-25.1'


@require_GET
def health(request):
    """Minimal deployment probe without account or configuration details."""
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
            cursor.fetchone()
    except Exception:
        return JsonResponse({'ok':False},status=503)
    response=JsonResponse({'ok':True,'service':'push','network':'stellar-testnet'})
    response['Cache-Control']='no-store'
    return response


@require_GET
def privacy(request):
    return render(request,'privacy.html')

def notify(recipient,kind,title,body,link=''):
    return Notification.objects.create(recipient=recipient,kind=kind,title=title,body=body,link=link)


def limited(request,scope,limit=12):
    # REMOTE_ADDR only: do not trust client-supplied forwarding headers.
    identity = f'{scope}:{request.META.get("REMOTE_ADDR", "unknown")}'
    key = hashlib.sha256(identity.encode()).hexdigest()
    now = timezone.now()
    with transaction.atomic():
        bucket,_ = RateBucket.objects.get_or_create(key=key,defaults={'expires':now+timedelta(minutes=15)})
        if bucket.expires <= now:
            RateBucket.objects.filter(pk=bucket.pk,expires__lte=now).update(count=0,expires=now+timedelta(minutes=15))
        return RateBucket.objects.filter(pk=bucket.pk,count__lt=limit).update(count=F('count')+1) == 0


def verified(view):
    @login_required
    @wraps(view)
    def wrapped(request,*args,**kwargs):
        if not request.user.email_verified:
            messages.error(request,'Enter the verification code from your email to unlock this area.')
            return redirect('verify_email')
        if not request.user.terms_accepted_at or request.user.terms_version != TERMS_VERSION:
            messages.info(request,'Review and accept the current Terms of Use to continue.')
            return redirect('accept_terms')
        sanction = request.user.sanctions.filter(active=True,kind__in=['suspension','ban']).order_by('-created_at').first()
        if sanction:
            return HttpResponse(f'Account access is restricted: {sanction.reason}',status=403)
        if request.method == 'POST' and limited(request,'writes',90):
            return HttpResponse('Too many requests. Please try again in 15 minutes.',status=429)
        return view(request,*args,**kwargs)
    return wrapped


def review_job_text(job):
    text = f'{job.title} {job.description} {job.deliverables}'.lower()
    flags=[]
    for phrase in ['pay outside','payment outside','telegram only','whatsapp only','send crypto first','registration fee']:
        if phrase in text: flags.append(f'Contains risky phrase: “{phrase}”.')
    return flags


def make_verification_code(subject_id):
    code = f'{secrets.randbelow(1_000_000):06d}'
    code_hash = salted_hmac('push.verify.code',f'{subject_id}:{code}').hexdigest()
    return code,code_hash


def deliver_verification_code(email,code,opening='Your Push verification code is:'):
    sent = send_mail(
        'Your Push verification code',
        f'{opening}\n\n{code}\n\nIt expires in 15 minutes. If you did not request this, ignore this email.',
        settings.DEFAULT_FROM_EMAIL,
        [email],
        fail_silently=False,
    )
    if sent != 1:
        raise RuntimeError('Verification email was not accepted by the email backend.')


def send_verification(user):
    code,code_hash = make_verification_code(user.pk)
    EmailVerificationCode.objects.update_or_create(
        user=user,
        defaults={'code_hash':code_hash,'expires_at':timezone.now()+timedelta(minutes=15),'attempts':0},
    )
    deliver_verification_code(user.email,code)


def send_registration_verification(pending):
    code,code_hash = make_verification_code(pending.pk)
    pending.code_hash = code_hash
    pending.expires_at = timezone.now()+timedelta(minutes=15)
    pending.attempts = 0
    pending.save(update_fields=['code_hash','expires_at','attempts','sent_at'])
    deliver_verification_code(pending.email,code,'Use this code to create your Push account:')


def issue_invitation(application,created_by):
    Invitation.objects.filter(
        application=application,used_at__isnull=True,revoked_at__isnull=True,
    ).update(revoked_at=timezone.now())
    code='PUSH-'+secrets.token_hex(4).upper()+'-'+secrets.token_hex(4).upper()
    invitation=Invitation.objects.create(
        application=application,email=application.email,code_hash=hash_invitation_code(code),
        created_by=created_by,expires_at=timezone.now()+timedelta(days=7),
    )
    return invitation,code


def remember_new_invitation(request,invitation,code):
    request.session['push_new_invitation']={
        'code':code,'email':invitation.email,
        'expires':timezone.localtime(invitation.expires_at).strftime('%d %b %Y, %H:%M'),
    }


def home(request):
    # The public landing page may show illustrative briefs, but never exposes
    # live tester jobs. Real opportunities belong to the invite-only product.
    sample_jobs = Job.objects.filter(status='open', moderation_status='approved', demo=True)[:3]
    return render(request,'home.html',{'jobs':sample_jobs})


def product(request):
    return render(request,'product.html')


def how_it_works(request):
    return render(request,'how_it_works.html')


def investors(request):
    return render(request,'investors.html')

def terms(request):
    return render(request,'terms.html',{'terms_version':TERMS_VERSION})

@login_required
def accept_terms(request):
    if request.user.terms_accepted_at and request.user.terms_version == TERMS_VERSION: return redirect('workspace')
    if request.method == 'POST':
        if request.POST.get('accept_terms') != 'on':
            messages.error(request,'Confirm that you have read and accept the Terms of Use.')
        else:
            request.user.terms_version=TERMS_VERSION;request.user.terms_accepted_at=timezone.now()
            request.user.save(update_fields=['terms_version','terms_accepted_at'])
            messages.success(request,'Terms accepted. Welcome to your workspace.')
            return redirect('workspace')
    return render(request,'accept_terms.html',{'terms_version':TERMS_VERSION})

def help_center(request):
    return render(request,'help.html')


def waitlist(request):
    if request.user.is_authenticated:
        return redirect('workspace')
    form=WaitlistForm(request.POST or None)
    if request.method == 'POST' and limited(request,'waitlist',5):
        return HttpResponse('Too many attempts. Please try again in 15 minutes.',status=429)
    if request.method == 'POST' and form.is_valid():
        values=form.cleaned_data
        with transaction.atomic():
            application,_=WaitlistApplication.objects.update_or_create(
                email=values['email'],
                defaults={
                    'name':values['name'],'role':values['role'],'skills':values['skills'],
                    'intended_use':values['intended_use'],'reason':values['reason'],
                    'accepted_testing_terms':True,'status':'pending','reviewed_by':None,'reviewed_at':None,
                },
            )
            # A new application starts a fresh review. Any earlier unused code
            # must stop working rather than silently bypass that review.
            Invitation.objects.filter(
                application=application,used_at__isnull=True,revoked_at__isnull=True,
            ).update(revoked_at=timezone.now())
        return render(request,'waitlist_received.html',{'application':application})
    return render(request,'waitlist.html',{'form':form})


def invite_redeem(request):
    if request.user.is_authenticated:
        return redirect('workspace')
    initial={'code':request.GET.get('code','')}
    form=InvitationCodeForm(request.POST or None,initial=initial)
    if request.method == 'POST' and limited(request,'invite',8):
        return HttpResponse('Too many attempts. Please try again in 15 minutes.',status=429)
    if request.method == 'POST' and form.is_valid():
        invitation=Invitation.objects.filter(
            code_hash=hash_invitation_code(form.cleaned_data['code']),used_at__isnull=True,
            revoked_at__isnull=True,expires_at__gt=timezone.now(),
        ).first()
        if invitation is None:
            form.add_error('code','That invitation is invalid, expired, revoked or already used.')
        else:
            remember_invitation(request,invitation)
            messages.success(request,f'Invitation accepted for {invitation.email}. Create your account using that email.')
            return redirect('register')
    return render(request,'invite.html',{'form':form})


def register(request):
    if request.user.is_authenticated: return redirect('workspace')
    invitation=current_invitation(request)
    if invitation is None:
        messages.info(request,'Push account creation is invite-only. Enter your invitation code first.')
        return redirect('invite_redeem')
    if request.method == 'POST' and limited(request,'register',6):
        return HttpResponse('Too many attempts. Please try again in 15 minutes.',status=429)
    form = Registration(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        email=form.cleaned_data['email']
        if invitation.email.casefold() != email.casefold():
            form.add_error('email',f'Use the approved email address: {invitation.email}')
            return render(request,'registration/register.html',{'form':form,'invitation':invitation})
        pending,_=PendingRegistration.objects.update_or_create(
            email=email,
            defaults={
                'display_name':form.cleaned_data['display_name'],
                'password_hash':make_password(form.cleaned_data['password1']),
                'code_hash':'',
                'expires_at':timezone.now()+timedelta(minutes=15),
                'attempts':0,
                'terms_version':TERMS_VERSION,
            },
        )
        request.session['pending_registration_id']=str(pending.pk)
        try: send_registration_verification(pending)
        except Exception:
            messages.error(request,'Your details are saved temporarily, but the code could not be delivered. Check email delivery settings and resend.')
        else: messages.success(request,'Enter the six-digit code from your email to create the account.')
        return redirect('verify_registration')
    return render(request,'registration/register.html',{'form':form,'invitation':invitation})


def pending_registration(request):
    pending_id=request.session.get('pending_registration_id')
    if not pending_id: return None
    return PendingRegistration.objects.filter(pk=pending_id).first()


def verify_registration(request):
    if request.user.is_authenticated: return redirect('workspace')
    pending=pending_registration(request)
    if pending is None:
        messages.info(request,'Start with your account details so Push knows where to send the code.')
        return redirect('register')
    form=VerificationCodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            pending=PendingRegistration.objects.select_for_update().filter(pk=pending.pk).first()
            if pending is None:
                messages.error(request,'That pending registration is no longer available. Start again.')
                return redirect('register')
            if pending.expires_at <= timezone.now():
                form.add_error('code','That code has expired. Send a new code and try again.')
            elif pending.attempts >= 5:
                form.add_error('code','Too many incorrect attempts. Send a new code.')
            else:
                expected=salted_hmac('push.verify.code',f'{pending.pk}:{form.cleaned_data["code"]}').hexdigest()
                if not hmac.compare_digest(pending.code_hash,expected):
                    pending.attempts=F('attempts')+1
                    pending.save(update_fields=['attempts'])
                    form.add_error('code','That code is incorrect. Check the email and try again.')
                elif User.objects.filter(email__iexact=pending.email).exists():
                    pending.delete()
                    request.session.pop('pending_registration_id',None)
                    messages.info(request,'That account already exists. Sign in instead.')
                    return redirect('login')
                else:
                    user=User(username=pending.email,email=pending.email,display_name=pending.display_name,
                              password=pending.password_hash,email_verified=True,terms_version=pending.terms_version,
                              terms_accepted_at=timezone.now())
                    user.save()
                    invitation=current_invitation(request,user.email,for_update=True)
                    if invitation is None:
                        user.delete()
                        form.add_error('code','Your invitation expired before account activation. Request a new invitation.')
                        return render(request,'registration/verify_registration.html',{'form':form,'pending':pending})
                    consume_invitation(request,user,invitation)
                    pending.delete()
                    request.session.pop('pending_registration_id',None)
                    login(request,user,backend='django.contrib.auth.backends.ModelBackend')
                    messages.success(request,'Email verified and account created. Welcome to Push.')
                    return redirect('workspace')
    return render(request,'registration/verify_registration.html',{'form':form,'pending':pending})


@require_POST
def resend_registration(request):
    pending=pending_registration(request)
    if pending is None: return redirect('register')
    if limited(request,'registration-resend',3):
        return HttpResponse('Please wait before requesting another code.',status=429)
    try: send_registration_verification(pending)
    except Exception: messages.error(request,'We could not send a new code. Check the protected email delivery settings.')
    else: messages.success(request,'A new six-digit code has been sent.')
    return redirect('verify_registration')


class SignIn(LoginView):
    template_name = 'registration/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True
    def dispatch(self,request,*args,**kwargs):
        if request.method == 'POST' and limited(request,'login'):
            return HttpResponse('Too many attempts. Please try again in 15 minutes.',status=429)
        return super().dispatch(request,*args,**kwargs)


class Recovery(PasswordResetView):
    template_name = 'registration/reset.html'
    email_template_name = 'registration/reset_email.txt'
    subject_template_name = 'registration/reset_subject.txt'
    form_class = RecoveryForm
    success_url = reverse_lazy('password_reset_done')
    def dispatch(self,request,*args,**kwargs):
        if request.method == 'POST' and limited(request,'recovery',5):
            return HttpResponse('Too many attempts. Please try again in 15 minutes.',status=429)
        return super().dispatch(request,*args,**kwargs)


@login_required
def verify_email(request):
    if request.user.email_verified:
        return redirect('workspace')
    record = EmailVerificationCode.objects.filter(user=request.user,expires_at__gt=timezone.now()).first()
    if request.method == 'GET' and record is None:
        try:
            send_verification(request.user)
        except Exception:
            messages.error(request,'We could not create a verification email. Use “Send a new code” to try again.')
    form = VerificationCodeForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        record = EmailVerificationCode.objects.filter(user=request.user).first()
        if not record or record.expires_at <= timezone.now():
            if record: record.delete()
            form.add_error('code','That code has expired. Send a new code and try again.')
        elif record.attempts >= 5:
            record.delete()
            form.add_error('code','Too many incorrect attempts. Send a new code.')
        else:
            expected = salted_hmac('push.verify.code',f'{request.user.pk}:{form.cleaned_data["code"]}').hexdigest()
            if not hmac.compare_digest(record.code_hash,expected):
                record.attempts = F('attempts') + 1
                record.save(update_fields=['attempts'])
                form.add_error('code','That code is incorrect. Check the email and try again.')
            else:
                User.objects.filter(pk=request.user.pk,email_verified=False).update(email_verified=True)
                record.delete()
                request.user.email_verified = True
                messages.success(request,'Email verified. Wallet, Messages and work actions are now available.')
                return redirect('workspace')
    return render(request,'registration/verify_code.html',{'form':form})


def verify_link(request,code):
    try:
        data = signing.loads(code,salt='push.verify',max_age=86400)
        user = User.objects.get(pk=data['id'],email=data['email'],is_active=True,email_verified=False)
    except (signing.BadSignature,User.DoesNotExist,KeyError):
        return render(request,'notice.html',{'title':'This link is no longer valid','description':'Sign in and request a new verification email from your workspace.'},status=400)
    if request.method == 'POST':
        User.objects.filter(pk=user.pk,email_verified=False).update(email_verified=True)
        EmailVerificationCode.objects.filter(user=user).delete()
        messages.success(request,'Email verified. You can now post jobs and apply for work.')
        return redirect('workspace' if request.user.is_authenticated else 'login')
    return render(request,'verify.html')


@login_required
@require_POST
def resend(request):
    if request.user.email_verified: return redirect('workspace')
    if limited(request,'verify-resend',3):
        return HttpResponse('Please wait before requesting another email.',status=429)
    try: send_verification(request.user)
    except Exception: messages.error(request,'We could not send a verification code. Check the email delivery settings and try again.')
    else: messages.success(request,'A new six-digit verification code has been sent.')
    return redirect('verify_email')


@verified
def workspace(request):
    assignments = Assignment.objects.filter(Q(worker=request.user)|Q(job__owner=request.user)).select_related('job','worker')
    worker_assignments=Assignment.objects.filter(worker=request.user)
    verified=Payment.objects.filter(assignment__worker=request.user,simulated=False).aggregate(total=Sum('amount'))['total'] or 0
    simulated=Payment.objects.filter(assignment__worker=request.user,simulated=True).aggregate(total=Sum('amount'))['total'] or 0
    pending=worker_assignments.filter(status__in=['awaiting_funding','funded','submitted']).aggregate(total=Sum('budget'))['total'] or 0
    completed=worker_assignments.filter(status='paid').count()
    active=worker_assignments.filter(status__in=['awaiting_funding','funded','submitted']).count()
    participant_messages=Message.objects.filter(Q(assignment__worker=request.user)|Q(assignment__job__owner=request.user)).distinct()
    message_count=participant_messages.count()
    return render(request,'workspace.html',{'assignments':assignments,'own_jobs':Job.objects.filter(owner=request.user),
        'applications':Application.objects.filter(worker=request.user).select_related('job'),
        'verified_earnings':verified,'simulated_earnings':simulated,'pending_earnings':pending,
        'total_earnings':verified+simulated,'completed_count':completed,'active_count':active,
        'message_count':message_count,'recent_messages':participant_messages.select_related('sender','assignment__job').order_by('-created_at')[:3]})


@verified
def work(request):
    assigned=Assignment.objects.filter(worker=request.user).select_related('job','job__owner').order_by('-created_at')
    hiring=Assignment.objects.filter(job__owner=request.user).select_related('job','worker').order_by('-created_at')
    posted=Job.objects.filter(owner=request.user).order_by('-created_at')
    applications=Application.objects.filter(worker=request.user).select_related('job','job__owner').order_by('-created_at')
    return render(request,'work.html',{'assigned':assigned,'hiring':hiring,'posted':posted,'applications':applications})


@verified
def assigned_work(request):
    records=(Assignment.objects.filter(worker=request.user)
        .select_related('job','job__owner')
        .order_by('-created_at'))
    needs_action=records.filter(status__in=['awaiting_acceptance','funded'])
    in_progress=records.exclude(status__in=['awaiting_acceptance','funded','paid','cancelled'])
    finished=records.filter(status__in=['paid','cancelled'])
    return render(request,'assigned_work.html',{
        'needs_action':needs_action,
        'in_progress':in_progress,
        'finished':finished,
        'assigned_total':records.count(),
    })


@login_required
@require_GET
def activity_status(request):
    unread=Notification.objects.filter(recipient=request.user,read_at__isnull=True)
    active_assigned=Assignment.objects.filter(worker=request.user).exclude(status__in=['paid','cancelled'])
    worker_actions=active_assigned.filter(status__in=['awaiting_acceptance','funded']).count()
    client_actions=Assignment.objects.filter(
        job__owner=request.user,status__in=['awaiting_funding','submitted']
    ).count()
    latest=unread.order_by('-created_at').first()
    response=JsonResponse({
        'notifications':unread.count(),
        'messages':unread.filter(kind='message').count(),
        'assigned':active_assigned.count(),
        'work_attention':worker_actions+client_actions,
        'latest':({'id':latest.pk,'title':latest.title,'link':latest.link} if latest else None),
    })
    response['Cache-Control']='no-store'
    return response


@verified
def notifications(request):
    records=Notification.objects.filter(recipient=request.user)
    return render(request,'notifications.html',{'notifications':records[:100]})


@verified
@require_POST
def notification_read(request,pk):
    item=get_object_or_404(Notification,pk=pk,recipient=request.user)
    if item.read_at is None:
        item.read_at=timezone.now();item.save(update_fields=['read_at'])
    if item.link.startswith('/') and not item.link.startswith('//'):
        return redirect(item.link)
    return redirect('notifications')


@verified
@require_POST
def notifications_read_all(request):
    Notification.objects.filter(recipient=request.user,read_at__isnull=True).update(read_at=timezone.now())
    return redirect('notifications')


@verified
def wallet(request):
    request_uri=None
    balances=None
    balance_error=''
    if request.user.stellar_address:
        try:
            balances=account_balances(request.user.stellar_address)
        except StellarVerificationError as exc:
            balance_error=str(exc)
    form=WalletRequestForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        destination=form.cleaned_data['destination']
        if '@' in destination:
            recipient=User.objects.filter(email__iexact=destination).only('stellar_address').first()
            if not recipient or not recipient.stellar_address:
                form.add_error('destination','That recipient is not ready to receive testnet payments through Push.')
            else:
                destination=recipient.stellar_address
        if not form.errors:
            request_uri=payment_uri(destination=destination,amount=form.cleaned_data['amount'],
                memo=form.cleaned_data['memo'] or 'Push test payment',asset=form.cleaned_data['asset'])
    return render(request,'wallet.html',{
        'form':form,'request_uri':request_uri,'balances':balances,'balance_error':balance_error,
    })


@verified
def payments(request):
    records=Payment.objects.filter(assignment__worker=request.user).select_related('assignment__job')
    network_total=records.filter(simulated=False).aggregate(total=Sum('amount'))['total'] or 0
    simulated_total=records.filter(simulated=True).aggregate(total=Sum('amount'))['total'] or 0
    pending=Assignment.objects.filter(worker=request.user,status__in=['awaiting_funding','funded','submitted']).aggregate(total=Sum('budget'))['total'] or 0
    return render(request,'payments.html',{'payments':records,'verified_earnings':network_total,
        'simulated_earnings':simulated_total,'total_earnings':network_total+simulated_total,'pending_earnings':pending})


def conversation_list(user):
    return (Assignment.objects.filter(Q(worker=user)|Q(job__owner=user))
        .select_related('job','job__owner','worker')
        .annotate(latest_message_at=Max('messages__created_at'))
        .order_by(F('latest_message_at').desc(nulls_last=True),'-created_at'))


@verified
def inbox(request):
    return render(request,'messages.html',{'conversations':conversation_list(request.user),'message_form':MessageForm()})


@verified
def conversation(request,pk):
    item=participant_assignment(request,pk)
    Notification.objects.filter(recipient=request.user,kind='message',link=f'/messages/{item.pk}/',read_at__isnull=True).update(read_at=timezone.now())
    form=MessageForm(request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            record=form.save(commit=False);record.assignment=item;record.sender=request.user;record.save()
            recipient=item.worker if item.job.owner_id == request.user.pk else item.job.owner
            notify(recipient,'message',f'New message from {request.user.display_name}',item.job.title,f'/messages/{item.pk}/')
            return redirect('conversation',pk=item.pk)
        messages.error(request,'Write a message of 2,000 characters or fewer.')
    return render(request,'messages.html',{'conversations':conversation_list(request.user),'active':item,
        'message_form':form,'other_person':item.worker if item.job.owner_id == request.user.pk else item.job.owner})


@verified
@require_POST
def wallet_connect(request):
    try:
        payload=json.loads(request.body or '{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({'ok':False,'message':'The wallet response was not valid.'},status=400)
    address=str(payload.get('address','')).strip()
    network=str(payload.get('network','')).upper().strip()
    if network != 'TESTNET':
        return JsonResponse({'ok':False,'message':'Switch Freighter to Stellar testnet and try again.'},status=400)
    if not valid_account_id(address):
        return JsonResponse({'ok':False,'message':'Freighter did not return a valid Stellar public address.'},status=400)
    request.user.stellar_address=address
    request.user.save(update_fields=['stellar_address'])
    return JsonResponse({'ok':True,'message':'Freighter connected on Stellar testnet.','address':address})


@login_required
def profile(request):
    form = ProfileForm(request.POST or None,request.FILES or None,instance=request.user)
    if request.method == 'POST' and form.is_valid():
        user=form.save(commit=False)
        if form.cleaned_data.get('remove_profile_image'):
            user.profile_image=None;user.profile_image_content_type=''
        image=form.cleaned_data.get('profile_image')
        if image:
            user.profile_image=image.read();user.profile_image_content_type=image.push_content_type
        if form.cleaned_data.get('remove_resume'):
            user.resume_file=None;user.resume_filename=''
        resume=form.cleaned_data.get('resume_file')
        if resume:
            user.resume_file=resume.read();user.resume_filename=os.path.basename(resume.name)[:160]
        user.save()
        messages.success(request,'Profile saved. Your email stays private.')
        return redirect('profile')
    return render(request,'profile.html',{'form':form})


def public_profile(request,pk):
    person = get_object_or_404(User,pk=pk,public_profile=True,is_active=True)
    return render(request,'public_profile.html',{'person':person})


@require_GET
def profile_image(request,pk):
    person=get_object_or_404(User,pk=pk,is_active=True)
    if not person.public_profile and not (request.user.is_authenticated and (request.user.pk==person.pk or request.user.is_staff)):
        raise Http404
    if not person.profile_image: raise Http404
    content_type=person.profile_image_content_type if person.profile_image_content_type in {'image/jpeg','image/png','image/webp'} else 'application/octet-stream'
    response=HttpResponse(bytes(person.profile_image),content_type=content_type)
    response['Cache-Control']='public, max-age=3600' if person.public_profile else 'private, max-age=300'
    response['X-Content-Type-Options']='nosniff'
    return response


@require_GET
def resume_download(request,pk):
    person=get_object_or_404(User,pk=pk,is_active=True)
    if not person.public_profile and not (request.user.is_authenticated and (request.user.pk==person.pk or request.user.is_staff)):
        raise Http404
    if not person.resume_file: raise Http404
    filename=person.resume_filename or 'resume.pdf'
    response=HttpResponse(bytes(person.resume_file),content_type='application/pdf')
    response['Content-Disposition']=f"attachment; filename*=UTF-8''{quote(filename)}"
    response['Cache-Control']='private, no-store'
    response['X-Content-Type-Options']='nosniff'
    response['Content-Security-Policy']="default-src 'none'; sandbox"
    return response


@never_cache
@verified
def jobs(request):
    qs = Job.objects.filter(status='open',moderation_status='approved').select_related('owner')
    q = request.GET.get('q','').strip()[:120]
    category = request.GET.get('category','')
    if q:
        qs = qs.filter(
            Q(title__icontains=q)|Q(project__icontains=q)|Q(description__icontains=q)|
            Q(deliverables__icontains=q)|Q(category__icontains=q)
        )
    if category: qs = qs.filter(category=category)
    from django.core.paginator import Paginator
    page = Paginator(qs,20).get_page(request.GET.get('page'))
    categories = [choice for choice,_label in Job._meta.get_field('category').choices]
    return render(request,'jobs.html',{'jobs':page,'q':q,'category':category,'categories':categories})


@verified
def job_create(request):
    form = JobForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        job = form.save(commit=False)
        job.owner = request.user
        flags=review_job_text(job)
        job.moderation_status='review' if flags else 'approved'
        job.moderation_notes='\n'.join(flags)
        job.save()
        if flags:
            messages.success(request,'Job saved for moderator review. You will receive a notification after the decision.')
        else:
            messages.success(request,'Job published. It is now visible in Find work and searchable by other members.')
        return redirect('job_detail',pk=job.pk)
    return render(request,'job_form.html',{'form':form})


@verified
def job_edit(request,pk):
    job = get_object_or_404(Job,pk=pk,owner=request.user,demo=False)
    if job.status != 'open' or job.applications.exists():
        return HttpResponse('This brief is locked because it is closed, assigned, or already has applications.',status=409)
    form = JobForm(request.POST or None,instance=job)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            # Applicant-changing actions update this same row first. Doing so
            # here prevents an edit racing with the first application.
            if not Job.objects.filter(pk=job.pk,status='open',demo=False).update(status='open'):
                return HttpResponse('This brief changed. Refresh before editing again.',status=409)
            if Application.objects.filter(job_id=job.pk).exists():
                return HttpResponse('An application arrived, so the original terms are now locked.',status=409)
            locked = Job.objects.get(pk=job.pk)
            for field in form._meta.fields:
                setattr(locked,field,form.cleaned_data[field])
            flags=review_job_text(locked)
            locked.moderation_status='review' if flags else 'approved'
            locked.moderation_notes='\n'.join(flags)
            locked.save(update_fields=[*form._meta.fields,'moderation_status','moderation_notes'])
        if flags:
            messages.success(request,'Job updated and sent for moderator review because its wording needs a safety check.')
        else:
            messages.success(request,'Job updated and visible in Find work. It will lock when the first application arrives.')
        return redirect('job_detail',pk=job.pk)
    return render(request,'job_form.html',{'form':form,'editing':True,'job':job})


@verified
def job_detail(request,pk):
    job = get_object_or_404(Job.objects.select_related('owner'),pk=pk)
    is_owner = request.user.is_authenticated and job.owner_id == request.user.pk
    if job.moderation_status != 'approved' and not (is_owner or (request.user.is_authenticated and request.user.is_staff)):
        raise Http404
    existing = request.user.is_authenticated and Application.objects.filter(job=job,worker=request.user).first()
    can_edit = is_owner and job.status == 'open' and not job.demo and not job.applications.exists()
    return render(request,'job_detail.html',{'job':job,'is_owner':is_owner,'can_edit':can_edit,'existing':existing,'form':ApplicationForm(),
        'applications':job.applications.select_related('worker') if is_owner else [],
        'active_assignment':Assignment.objects.filter(job=job).first() if is_owner else None})


@verified
@require_POST
def apply(request,pk):
    job = get_object_or_404(Job,pk=pk)
    if job.owner_id == request.user.pk: return HttpResponseForbidden('You cannot apply to your own job.')
    if job.status != 'open' or job.demo or job.moderation_status != 'approved': return HttpResponseBadRequest('This job is not accepting applications.')
    form = ApplicationForm(request.POST)
    if form.is_valid():
        try:
            with transaction.atomic():
                if not Job.objects.filter(pk=job.pk,status='open',demo=False).update(status='open'):
                    return HttpResponse('This job is no longer accepting applications.',status=409)
                Application.objects.create(job=job,worker=request.user,proposal=form.cleaned_data['proposal'])
        except IntegrityError: messages.info(request,'You have already applied to this job.')
        else:
            messages.success(request,'Application sent. Your proposal is visible only to you and the hiring account.')
            notify(job.owner,'application','New application received',f'{request.user.display_name} applied for {job.title}.',f'/jobs/{job.pk}/')
        return redirect('job_detail',pk=job.pk)
    return render(request,'application_form.html',{'form':form,'job':job},status=400)


@verified
@require_POST
def select(request,pk):
    application = get_object_or_404(Application.objects.select_related('job','worker'),pk=pk,job__owner=request.user)
    with transaction.atomic():
        # All applicant changes first lock the same job via an update. This also
        # serialises these operations on the local SQLite database.
        changed = Job.objects.filter(pk=application.job_id,status='open',demo=False).update(status='open')
        if not changed: return HttpResponse('This job is no longer accepting selections.',status=409)
        if Application.objects.get(pk=application.pk).withdrawn:
            return HttpResponse('This application has been withdrawn.',status=409)
        Job.objects.filter(pk=application.job_id).update(status='assigned')
        snapshot={
            'title':application.job.title,'project':application.job.project,
            'description':application.job.description,'deliverables':application.job.deliverables,
            'acceptance_criteria':application.job.acceptance_criteria,'budget':application.job.budget,
            'deadline':application.job.deadline.isoformat(),'revision_limit':application.job.revision_limit,
            'response_days':application.job.response_days,
        }
        assignment = Assignment.objects.create(job=application.job,worker=application.worker,
            scope=application.job.deliverables,budget=application.job.budget,agreement_snapshot=snapshot)
        Event.objects.create(assignment=assignment,actor=request.user,kind='Worker selected')
        notify(application.worker,'selection','You were selected',f'{application.job.owner.display_name} selected you for {application.job.title}.',f'/assignments/{assignment.pk}/')
    messages.success(request,'Worker selected. They must accept the agreed scope before simulated funding.')
    return redirect('assignment',pk=assignment.pk)


def participant_assignment(request,pk):
    return get_object_or_404(Assignment.objects.select_related('job','worker').filter(
        Q(job__owner=request.user)|Q(worker=request.user)),pk=pk)


@verified
def assignment(request,pk):
    item = participant_assignment(request,pk)
    stellar_request = None
    if item.status == 'submitted' and item.payment_method == 'stellar_usdc_testnet' and item.worker.stellar_address:
        memo = assignment_memo(item.id)
        stellar_request = {
            'memo':memo,
            'uri':payment_uri(destination=item.worker.stellar_address,amount=item.budget,memo=memo),
            'destination':item.worker.stellar_address,
        }
    return render(request,'assignment.html',{
        'item':item,
        'is_owner':item.job.owner_id==request.user.pk,
        'submission_form':SubmissionForm(),
        'message_form':MessageForm(),
        'stellar_request':stellar_request,
    })


@verified
@require_POST
def assignment_message(request,pk):
    item=participant_assignment(request,pk)
    form=MessageForm(request.POST)
    if not form.is_valid():
        messages.error(request,'Write a message of 2,000 characters or fewer.')
        return redirect('assignment',pk=item.pk)
    message=form.save(commit=False);message.assignment=item;message.sender=request.user;message.save()
    recipient=item.worker if item.job.owner_id == request.user.pk else item.job.owner
    notify(recipient,'message',f'New message from {request.user.display_name}',item.job.title,f'/messages/{item.pk}/')
    return redirect('assignment',pk=item.pk)


@verified
@require_POST
def assignment_action(request,pk):
    item = participant_assignment(request,pk)
    form = ActionForm(request.POST)
    if not form.is_valid(): return HttpResponseBadRequest('Invalid action. Return to the assignment and try again.')
    action = form.cleaned_data['action']
    owner = item.job.owner_id == request.user.pk
    note = form.cleaned_data['note']
    transitions = {
        'accept':('awaiting_acceptance','awaiting_funding',not owner),
        'fund':('awaiting_funding','funded',owner),
        'submit':('funded','submitted',not owner),
        'revise':('submitted','funded',owner),
        'approve':('submitted','paid',owner),
    }
    submission = None
    if action == 'dispute':
        if item.status not in ['funded','submitted'] or not note: return HttpResponseBadRequest('A reason and an active funded assignment are required.')
        expected,new,allowed = item.status,'disputed',True
    elif action == 'cancel':
        expected,new,allowed = item.status,'cancelled',item.status in ['awaiting_acceptance','awaiting_funding']
    elif action in transitions: expected,new,allowed = transitions[action]
    else: return HttpResponseBadRequest('Unsupported action.')
    if not allowed: return HttpResponseForbidden('You cannot perform this action.')
    if action == 'fund' and not form.cleaned_data['payment_method']: return HttpResponseBadRequest('Choose a payment method.')
    if action == 'fund' and form.cleaned_data['payment_method'] == 'stellar_usdc_testnet' and not item.worker.stellar_address:
        return HttpResponseBadRequest('The worker must add a Stellar testnet receiving address before this route can be selected.')
    if action == 'revise' and not note: return HttpResponseBadRequest('Describe the requested revision.')
    if action == 'accept' and not form.cleaned_data['accept_terms']:
        return HttpResponseBadRequest('Read the agreement and confirm the terms before accepting.')
    if action == 'revise' and item.revisions_used >= item.job.revision_limit:
        return HttpResponseBadRequest('The included revision limit has been reached. Open a dispute or agree new terms in messages.')
    if action == 'submit':
        submission = SubmissionForm(request.POST)
        if not submission.is_valid():
            return render(request,'assignment.html',{'item':item,'is_owner':owner,'submission_form':submission},status=400)
    stellar_hash = None
    if action == 'approve' and item.payment_method == 'stellar_usdc_testnet':
        transaction_hash = form.cleaned_data['transaction_hash']
        if not transaction_hash:
            return HttpResponseBadRequest('Enter the Stellar testnet transaction hash after sending payment.')
        if Payment.objects.filter(transaction_hash__iexact=transaction_hash).exists():
            return HttpResponse('That Stellar transaction has already been used.',status=409)
        try:
            stellar_hash = verify_payment(
                transaction_hash=transaction_hash,
                destination=item.worker.stellar_address,
                amount=item.budget,
                memo=assignment_memo(item.id),
            )
        except StellarVerificationError as exc:
            messages.error(request,str(exc))
            return redirect('assignment',pk=item.pk)
    with transaction.atomic():
        fields = {'status':new}
        if action == 'fund': fields['payment_method'] = form.cleaned_data['payment_method']
        if action == 'accept': fields['accepted_terms_at'] = timezone.now()
        if action == 'submit': fields['client_response_due'] = timezone.now()+timedelta(days=item.job.response_days)
        if action == 'revise':
            fields['revisions_used'] = F('revisions_used')+1
            fields['client_response_due'] = None
        if not Assignment.objects.filter(pk=item.pk,status=expected).update(**fields):
            return HttpResponse('Assignment changed. Refresh before trying again.',status=409)
        if submission:
            record = submission.save(commit=False)
            record.assignment = item
            record.author = request.user
            record.save()
        if action == 'dispute':
            Dispute.objects.create(assignment=item,opened_by=request.user,reason=note)
        if action == 'approve':
            Payment.objects.create(
                assignment=item,
                amount=item.budget,
                method=item.payment_method,
                simulated=not bool(stellar_hash),
                network='stellar_testnet' if stellar_hash else '',
                transaction_hash=stellar_hash,
            )
            Job.objects.filter(pk=item.job_id).update(status='completed')
        Event.objects.create(assignment=item,actor=request.user,kind=action,note=note)
        recipient=item.worker if owner else item.job.owner
        event_copy={
            'accept':('Agreement accepted',f'{item.worker.display_name} accepted {item.job.title}.'),
            'fund':('Job ready to begin',f'The payment route for {item.job.title} was recorded.'),
            'submit':('Work submitted',f'{item.worker.display_name} submitted delivery evidence.'),
            'revise':('Revision requested',f'A revision was requested for {item.job.title}.'),
            'approve':('Work approved',f'{item.job.title} was approved and its payment record updated.'),
            'dispute':('Dispute opened',f'Release for {item.job.title} is paused for review.'),
            'cancel':('Agreement cancelled',f'The agreement for {item.job.title} was cancelled.'),
        }
        title,body=event_copy[action]
        notify(recipient,action,title,body,f'/assignments/{item.pk}/')
    messages.success(request,{'fund':'Payment route selected.','approve':('Stellar testnet payment verified.' if stellar_hash else 'Approval recorded and payment simulated. No money moved.'),
        'dispute':'Dispute opened. Release is blocked while an administrator reviews the record.'}.get(action,'Assignment updated.'))
    return redirect('assignment',pk=item.pk)


@login_required
def moderation(request):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    disputes=Dispute.objects.select_related('assignment__job','opened_by','assignment__worker').order_by('status','-created_at')
    flagged=Job.objects.filter(moderation_status='review').select_related('owner')
    waitlist_items=WaitlistApplication.objects.select_related('reviewed_by')[:100]
    invitations=Invitation.objects.select_related('application','created_by','used_by')[:100]
    return render(request,'moderation.html',{
        'disputes':disputes,'flagged_jobs':flagged,'waitlist_items':waitlist_items,
        'invitations':invitations,'invitation_form':StaffInvitationForm(),
        'new_invitation':request.session.pop('push_new_invitation',None),
        'moderation_now':timezone.now(),
        'metrics':{'open_disputes':disputes.exclude(status='resolved').count(),
                   'jobs':Job.objects.count(),'assignments':Assignment.objects.count(),
                   'recorded_value':Payment.objects.aggregate(total=Sum('amount'))['total'] or 0,
                   'waitlist':WaitlistApplication.objects.filter(status='pending').count()},
    })


@login_required
@require_POST
def review_waitlist(request,pk):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    application=get_object_or_404(WaitlistApplication,pk=pk)
    decision=request.POST.get('decision')
    if decision not in {'approve','reject'}:
        return HttpResponseBadRequest('Choose approve or reject.')
    with transaction.atomic():
        application=WaitlistApplication.objects.select_for_update().get(pk=application.pk)
        application.status='approved' if decision == 'approve' else 'rejected'
        application.reviewed_by=request.user
        application.reviewed_at=timezone.now()
        application.save(update_fields=['status','reviewed_by','reviewed_at'])
        Invitation.objects.filter(application=application,used_at__isnull=True,revoked_at__isnull=True).update(revoked_at=timezone.now())
        invitation,code=issue_invitation(application,request.user) if decision == 'approve' else (None,'')
    if decision == 'approve':
        remember_new_invitation(request,invitation,code)
        try:
            send_mail(
                'Your Push testing invitation',
                f'You have been approved to test Push.\n\nInvitation code: {code}\n\nEnter it at {request.build_absolute_uri(reverse("invite_redeem"))}\n\nThis code expires in 7 days, works once, and is tied to {application.email}. Testnet assets have no monetary value and testing does not guarantee payment.',
                settings.DEFAULT_FROM_EMAIL,[application.email],fail_silently=False,
            )
        except Exception:
            messages.warning(request,f'Approved, but email delivery failed. Give this code to {application.email} securely: {code}')
        else:
            messages.success(request,f'Approved and sent a one-time invitation to {application.email}.')
    else:
        messages.success(request,f'{application.email} was not approved for this testing round.')
    return redirect('moderation')


@login_required
@require_POST
def create_staff_invitation(request):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    form=StaffInvitationForm(request.POST)
    if not form.is_valid():
        detail=' '.join(str(error) for errors in form.errors.values() for error in errors)
        messages.error(request,f'The invitation was not created. {detail}')
        return redirect('moderation')
    with transaction.atomic():
        application,_=WaitlistApplication.objects.update_or_create(
            email=form.cleaned_data['email'],
            defaults={
                'name':form.cleaned_data['name'],'role':form.cleaned_data['role'] or 'Invited tester',
                'skills':'','intended_use':'Direct invitation from the Push testing team.',
                'reason':'Invited directly by an authorised Push founder or moderator.',
                'accepted_testing_terms':False,'status':'approved','reviewed_by':request.user,
                'reviewed_at':timezone.now(),
            },
        )
        invitation,code=issue_invitation(application,request.user)
    remember_new_invitation(request,invitation,code)
    try:
        send_mail(
            'Your Push testing invitation',
            f'You have been invited to test Push.\n\nInvitation code: {code}\n\nEnter it at {request.build_absolute_uri(reverse("invite_redeem"))}\n\nThis code expires in 7 days, works once, and is tied to {application.email}. Testnet assets have no monetary value and testing does not guarantee payment.',
            settings.DEFAULT_FROM_EMAIL,[application.email],fail_silently=False,
        )
    except Exception:
        messages.warning(request,'The code was created, but email delivery failed. Copy it from the secure one-time panel below.')
    else:
        messages.success(request,f'Invitation created and emailed to {application.email}.')
    return redirect('moderation')


@login_required
@require_POST
def revoke_invitation(request,pk):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    updated=Invitation.objects.filter(pk=pk,used_at__isnull=True,revoked_at__isnull=True).update(revoked_at=timezone.now())
    messages.success(request,'Invitation revoked.' if updated else 'That invitation was already used or revoked.')
    return redirect('moderation')


@login_required
def moderate_dispute(request,pk):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    dispute=get_object_or_404(Dispute.objects.select_related('assignment__job','assignment__worker','opened_by'),pk=pk)
    form=DisputeResolutionForm(request.POST or None)
    sanction_form=SanctionForm(prefix='sanction')
    if request.method == 'POST' and form.is_valid():
        if dispute.status == 'resolved': return HttpResponse('This dispute is already resolved.',status=409)
        item=dispute.assignment; resolution=form.cleaned_data['resolution']; split=form.cleaned_data['split_percent']
        with transaction.atomic():
            dispute.status='resolved'; dispute.resolution=resolution; dispute.split_percent=split
            dispute.decision_note=form.cleaned_data['decision_note']; dispute.moderator=request.user; dispute.resolved_at=timezone.now()
            dispute.save()
            if resolution in ['release','split']:
                amount=item.budget if resolution == 'release' else max(1,round(item.budget*split/100))
                Payment.objects.get_or_create(assignment=item,defaults={'amount':amount,'method':item.payment_method or 'moderated','simulated':True})
                item.status='paid'; Job.objects.filter(pk=item.job_id).update(status='completed')
            elif resolution == 'revision': item.status='funded'; item.client_response_due=None
            else: item.status='cancelled'
            item.save(update_fields=['status','client_response_due'])
            Event.objects.create(assignment=item,actor=request.user,kind=f'Dispute: {resolution}',note=dispute.decision_note[:500])
        messages.success(request,'Dispute decision recorded. Any payment shown remains a simulation.')
        return redirect('moderate_dispute',pk=dispute.pk)
    return render(request,'moderate_dispute.html',{'dispute':dispute,'form':form,'sanction_form':sanction_form})


@login_required
@require_POST
def moderate_job(request,pk):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    job=get_object_or_404(Job,pk=pk)
    decision=request.POST.get('decision')
    if decision not in ['approved','removed']: return HttpResponseBadRequest('Choose approve or remove.')
    job.moderation_status=decision; job.save(update_fields=['moderation_status'])
    notify(job.owner,'moderation','Job review completed',f'{job.title} was {decision}.',f'/jobs/{job.pk}/')
    messages.success(request,'Listing moderation decision saved.')
    return redirect('moderation')


@login_required
@require_POST
def sanction_account(request,pk):
    if not request.user.is_staff: return HttpResponseForbidden('Moderator access required.')
    target=get_object_or_404(User,pk=pk)
    form=SanctionForm(request.POST,prefix='sanction')
    if not form.is_valid(): return HttpResponseBadRequest('Choose a sanction and give a reason.')
    sanction=form.save(commit=False); sanction.user=target; sanction.created_by=request.user; sanction.save()
    messages.success(request,'Account action recorded with an audit trail.')
    return redirect('moderation')


@verified
@require_POST
def job_close(request,pk):
    job = get_object_or_404(Job,pk=pk,owner=request.user,demo=False)
    if not Job.objects.filter(pk=job.pk,status='open').update(status='closed'):
        return HttpResponse('Only an open, unassigned job can be closed.',status=409)
    messages.success(request,'Job closed. Applications remain in your records; no new applications or selections are allowed.')
    return redirect('job_detail',pk=job.pk)


@verified
@require_POST
def withdraw(request,pk):
    application = get_object_or_404(Application,pk=pk,worker=request.user)
    with transaction.atomic():
        if not Job.objects.filter(pk=application.job_id,status='open',demo=False).update(status='open'):
            return HttpResponse('This job is no longer open. Manage any existing agreement from your workspace.',status=409)
        if not Application.objects.filter(pk=application.pk,withdrawn=False).update(withdrawn=True):
            return HttpResponse('This application has already been withdrawn.',status=409)
    messages.success(request,'Application withdrawn. Your record is retained, but the hiring account can no longer select it.')
    return redirect('workspace')
