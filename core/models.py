import uuid
from django.db import models
from django.db.models.functions import Lower
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)
    display_name = models.CharField(max_length=80)
    bio = models.TextField(max_length=1200,blank=True)
    skills = models.CharField(max_length=200,blank=True)
    portfolio = models.URLField(blank=True)
    profile_image = models.BinaryField(null=True,blank=True,editable=False)
    profile_image_content_type = models.CharField(max_length=32,blank=True,editable=False)
    resume_file = models.BinaryField(null=True,blank=True,editable=False)
    resume_filename = models.CharField(max_length=160,blank=True,editable=False)
    stellar_address = models.CharField(max_length=56,blank=True)
    public_profile = models.BooleanField(default=False)
    terms_version = models.CharField(max_length=20,blank=True)
    terms_accepted_at = models.DateTimeField(null=True,blank=True)
    class Meta:
        constraints = [models.UniqueConstraint(Lower('email'),name='unique_email_lower')]

class StaffAccess(models.Model):
    ROLE_CHOICES=[('owner','Owner'),('admin','Administrator'),('moderator','Moderator'),('support','Support')]
    STATUS_CHOICES=[('pending','Pending approval'),('approved','Approved'),('suspended','Suspended'),('revoked','Revoked')]
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='staff_access')
    role = models.CharField(max_length=20,choices=ROLE_CHOICES,default='moderator')
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    approved_by = models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='approved_staff_access')
    approved_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class EmailVerificationCode(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name='verification_code')
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(auto_now=True)
    attempts = models.PositiveSmallIntegerField(default=0)

class PendingRegistration(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=80)
    password_hash = models.CharField(max_length=128)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    sent_at = models.DateTimeField(auto_now=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    terms_version = models.CharField(max_length=20,default='2026-09-25')
    created_at = models.DateTimeField(auto_now_add=True)

class Job(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    owner = models.ForeignKey(User,on_delete=models.PROTECT)
    project = models.CharField(max_length=100)
    title = models.CharField(max_length=140)
    description = models.TextField(max_length=5000)
    deliverables = models.TextField(max_length=3000)
    acceptance_criteria = models.TextField(max_length=3000,blank=True)
    revision_limit = models.PositiveSmallIntegerField(default=2)
    response_days = models.PositiveSmallIntegerField(default=3)
    category = models.CharField(max_length=40,choices=[(x,x) for x in [
        'AI & Automation','Art & Illustration','Audio & Music','Business Consulting','Community Management',
        'Content Writing','Customer Support','Data & Analytics','Graphic Design','Marketing & Growth',
        'Mobile Development','Operations','Photography','Product Management','Research','Sales',
        'Social Media','Translation','UI/UX Design','Video Editing','Virtual Assistance','Web Development','Web3 & Blockchain']])
    budget = models.PositiveIntegerField(help_text='Illustrative USD budget. No funds collected.')
    deadline = models.DateField()
    status = models.CharField(max_length=20,default='open',choices=[('open','Open'),('assigned','Assigned'),('completed','Completed'),('closed','Closed')])
    demo = models.BooleanField(default=False)
    moderation_status = models.CharField(max_length=20,default='review',choices=[
        ('approved','Approved'),('review','Needs review'),('removed','Removed')])
    moderation_notes = models.TextField(max_length=1000,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']
        constraints = [models.CheckConstraint(condition=models.Q(budget__gt=0),name='positive_budget')]

class Application(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    job = models.ForeignKey(Job,on_delete=models.CASCADE,related_name='applications')
    worker = models.ForeignKey(User,on_delete=models.PROTECT)
    proposal = models.TextField(max_length=3000)
    withdrawn = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=['job','worker'],name='one_application_per_job')]

class Assignment(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    job = models.OneToOneField(Job,on_delete=models.PROTECT)
    worker = models.ForeignKey(User,on_delete=models.PROTECT)
    scope = models.TextField()
    budget = models.PositiveIntegerField()
    status = models.CharField(max_length=24,default='awaiting_acceptance',choices=[
        ('awaiting_acceptance','Awaiting agreement'),('awaiting_funding','Awaiting simulated funding'),
        ('funded','Ready for work'),('submitted','Ready for review'),('paid','Completed · simulated payment'),
        ('disputed','Dispute open'),('cancelled','Cancelled')])
    payment_method = models.CharField(max_length=32,blank=True,choices=[
        ('usdc','USDC simulation'),
        ('bank_card','Bank / card simulation'),
        ('stellar_usdc_testnet','Stellar USDC testnet'),
    ])
    agreement_snapshot = models.JSONField(default=dict,blank=True)
    client_response_due = models.DateTimeField(null=True,blank=True)
    revisions_used = models.PositiveSmallIntegerField(default=0)
    accepted_terms_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Submission(models.Model):
    assignment = models.ForeignKey(Assignment,on_delete=models.CASCADE,related_name='submissions')
    author = models.ForeignKey(User,on_delete=models.PROTECT)
    notes = models.TextField(max_length=3000)
    link = models.URLField(blank=True)
    evidence = models.TextField(max_length=3000,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['-created_at']

class Event(models.Model):
    assignment = models.ForeignKey(Assignment,on_delete=models.CASCADE,related_name='events')
    actor = models.ForeignKey(User,on_delete=models.PROTECT)
    kind = models.CharField(max_length=40)
    note = models.CharField(max_length=500,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']

class Message(models.Model):
    assignment = models.ForeignKey(Assignment,on_delete=models.CASCADE,related_name='messages')
    sender = models.ForeignKey(User,on_delete=models.PROTECT)
    body = models.TextField(max_length=2000)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering = ['created_at']

class Payment(models.Model):
    assignment = models.OneToOneField(Assignment,on_delete=models.PROTECT)
    amount = models.PositiveIntegerField()
    method = models.CharField(max_length=20)
    simulated = models.BooleanField(default=True,editable=False)
    network = models.CharField(max_length=20,blank=True)
    transaction_hash = models.CharField(max_length=64,blank=True,null=True,unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

class Dispute(models.Model):
    assignment = models.OneToOneField(Assignment,on_delete=models.PROTECT,related_name='dispute')
    opened_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='opened_disputes')
    reason = models.TextField(max_length=2000)
    evidence = models.TextField(max_length=3000,blank=True)
    status = models.CharField(max_length=20,default='open',choices=[('open','Open'),('under_review','Under review'),('resolved','Resolved')])
    resolution = models.CharField(max_length=20,blank=True,choices=[('release','Release to worker'),('refund','Refund client'),('split','Split'),('revision','Return for revision'),('cancel','Cancel agreement')])
    split_percent = models.PositiveSmallIntegerField(null=True,blank=True)
    decision_note = models.TextField(max_length=2000,blank=True)
    moderator = models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='moderated_disputes')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    resolved_at = models.DateTimeField(null=True,blank=True)

class AccountSanction(models.Model):
    user = models.ForeignKey(User,on_delete=models.PROTECT,related_name='sanctions')
    kind = models.CharField(max_length=20,choices=[('warning','Warning'),('suspension','Suspension'),('ban','Ban')])
    reason = models.TextField(max_length=1000)
    active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='issued_sanctions')
    created_at = models.DateTimeField(auto_now_add=True)

class Notification(models.Model):
    recipient = models.ForeignKey(User,on_delete=models.CASCADE,related_name='notifications')
    kind = models.CharField(max_length=30)
    title = models.CharField(max_length=140)
    body = models.CharField(max_length=300)
    link = models.CharField(max_length=300,blank=True)
    read_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']

class WaitlistApplication(models.Model):
    STATUS_CHOICES=[('pending','Pending'),('approved','Approved'),('rejected','Rejected')]
    name = models.CharField(max_length=80)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=80)
    skills = models.CharField(max_length=300,blank=True)
    intended_use = models.TextField(max_length=1200)
    reason = models.TextField(max_length=1200)
    accepted_testing_terms = models.BooleanField(default=False)
    status = models.CharField(max_length=20,choices=STATUS_CHOICES,default='pending')
    reviewed_by = models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='reviewed_waitlist_applications')
    reviewed_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering=['-created_at']

class Invitation(models.Model):
    id = models.UUIDField(primary_key=True,default=uuid.uuid4,editable=False)
    application = models.ForeignKey(WaitlistApplication,on_delete=models.PROTECT,related_name='invitations')
    email = models.EmailField()
    code_hash = models.CharField(max_length=64,unique=True)
    created_by = models.ForeignKey(User,on_delete=models.PROTECT,related_name='created_invitations')
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True,blank=True)
    used_by = models.ForeignKey(User,on_delete=models.PROTECT,null=True,blank=True,related_name='redeemed_invitations')
    revoked_at = models.DateTimeField(null=True,blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    class Meta:
        ordering=['-created_at']

class RateBucket(models.Model):
    key = models.CharField(max_length=64,unique=True)
    count = models.PositiveIntegerField(default=0)
    expires = models.DateTimeField()
