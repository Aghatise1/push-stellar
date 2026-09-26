from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordResetForm
from django.utils import timezone
from .models import User, Job, Application, Submission, Message, Dispute, AccountSanction
from .stellar import valid_account_id

STELLAR_ADDRESS_PATTERN = r'^G[A-Z2-7]{55}$'

class Registration(UserCreationForm):
    accept_terms = forms.BooleanField(label='I agree to the Push Terms of Use and Privacy Notice.')
    display_name = forms.CharField(
        max_length=80,
        label='Your name',
        help_text='The name shown in your workspace. You can change it later.',
        widget=forms.TextInput(attrs={'autocomplete':'name','placeholder':'Atise'}),
    )
    email = forms.EmailField(
        max_length=150,
        help_text='Used for sign-in and account recovery. It is never shown publicly.',
        widget=forms.EmailInput(attrs={'autocomplete':'email','placeholder':'you@example.com'}),
    )
    password1 = forms.CharField(
        label='Create a password', strip=False,
        help_text='Use at least 12 characters. Avoid your name, email and common passwords.',
        widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}),
    )
    password2 = forms.CharField(
        label='Confirm password', strip=False,
        help_text='Enter the same password again.',
        widget=forms.PasswordInput(attrs={'autocomplete':'new-password'}),
    )
    class Meta:
        model = User
        fields = ['display_name','email']
    def clean_email(self):
        email = self.cleaned_data['email'].strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('An account already uses this email. Sign in or reset your password.')
        return email
    def save(self,commit=True):
        user = super().save(commit=False)
        user.username = self.cleaned_data['email']
        if commit: user.save()
        return user

class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email',widget=forms.EmailInput(attrs={'autocomplete':'email'}))
    error_messages = {'invalid_login':'That email and password were not recognised. Check both fields or reset your password.','inactive':'This account is inactive.'}
    def clean_username(self):
        return self.cleaned_data['username'].strip().lower()

class RecoveryForm(PasswordResetForm):
    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()

    def get_users(self, email):
        """Allow Google-created accounts to set their first local password.

        Django's default implementation excludes users whose password is
        unusable. Social-login accounts begin in exactly that state, which made
        the recovery screen report success without sending any email.
        """
        return User.objects.filter(email__iexact=email, is_active=True).iterator()

class VerificationCodeForm(forms.Form):
    code = forms.RegexField(
        regex=r'^\d{6}$',
        label='Six-digit verification code',
        error_messages={'invalid':'Enter the six-digit code from your email.'},
        widget=forms.TextInput(attrs={
            'autocomplete':'one-time-code',
            'inputmode':'numeric',
            'pattern':'[0-9]*',
            'maxlength':'6',
            'placeholder':'000000',
        }),
    )

class ProfileForm(forms.ModelForm):
    stellar_address = forms.RegexField(
        regex=STELLAR_ADDRESS_PATTERN,
        required=False,
        label='Stellar testnet receiving address',
        help_text='Public G-address only. Never enter a secret key.',
        error_messages={'invalid':'Enter a valid public Stellar G-address.'},
    )
    class Meta:
        model = User
        fields = ['display_name','bio','skills','portfolio','stellar_address','public_profile']
        widgets = {'bio':forms.Textarea(attrs={'rows':4})}
    def clean_stellar_address(self):
        value = self.cleaned_data['stellar_address'].strip()
        if value and not valid_account_id(value):
            raise forms.ValidationError('That public Stellar address has an invalid checksum.')
        return value

class JobForm(forms.ModelForm):
    class Meta:
        model = Job
        fields = ['project','title','category','description','deliverables','acceptance_criteria','budget','deadline','revision_limit','response_days']
        widgets = {'deadline':forms.DateInput(attrs={'type':'date'}),'description':forms.Textarea(attrs={'rows':4}),
                   'deliverables':forms.Textarea(attrs={'rows':4}),'acceptance_criteria':forms.Textarea(attrs={'rows':4})}
        labels = {'acceptance_criteria':'How will successful delivery be judged?',
                  'project':'Project or company name','title':'What work do you need?',
                  'description':'Project outcome','deliverables':'Required deliverables',
                  'revision_limit':'Included revision rounds','response_days':'Client review window (days)'}
        help_texts = {'project':'The product, campaign or organisation this work belongs to.',
                      'title':'Use a clear title, such as “Edit four short product videos”.',
                      'description':'Explain the problem, audience, context and outcome you expect.',
                      'deliverables':'List exactly what the worker must hand over: files, formats, quantities and links.',
                      'acceptance_criteria':'Use observable checks, such as file formats, screen sizes or required sections.',
                      'budget':'The agreed amount for this job. This preview records it but does not hold or transfer money.',
                      'deadline':'The date the final delivery is expected.',
                      'revision_limit':'How many revision rounds are included before new terms are required.',
                      'response_days':'After delivery, the record shows when the client response is due.'}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        self.fields['revision_limit'].required=False
        self.fields['response_days'].required=False
    def clean_deadline(self):
        value = self.cleaned_data['deadline']
        if value < timezone.localdate(): raise forms.ValidationError('Choose today or a future deadline.')
        return value
    def clean_budget(self):
        value = self.cleaned_data['budget']
        if not 1 <= value <= 1000000: raise forms.ValidationError('Enter a budget between 1 and 1,000,000 USD.')
        return value
    def clean_revision_limit(self):
        value=self.cleaned_data.get('revision_limit')
        if value in [None,'']: return 2
        if not 0 <= value <= 10: raise forms.ValidationError('Choose between 0 and 10 revision rounds.')
        return value
    def clean_response_days(self):
        value=self.cleaned_data.get('response_days')
        if value in [None,'']: return 3
        if not 1 <= value <= 14: raise forms.ValidationError('Choose a review window between 1 and 14 days.')
        return value

class ApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['proposal']
        widgets = {'proposal':forms.Textarea(attrs={'rows':5})}

class SubmissionForm(forms.ModelForm):
    class Meta:
        model = Submission
        fields = ['notes','link','evidence']
        labels = {'evidence':'Delivery evidence or handover notes'}
        widgets = {'notes':forms.Textarea(attrs={'rows':4}),'evidence':forms.Textarea(attrs={'rows':4})}

class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ['body']
        labels = {'body':'Message'}
        widgets = {'body':forms.Textarea(attrs={'rows':3,'placeholder':'Keep decisions and questions attached to this assignment.'})}

class WalletRequestForm(forms.Form):
    destination = forms.RegexField(regex=STELLAR_ADDRESS_PATTERN,label='Recipient public address',error_messages={'invalid':'Enter a valid Stellar public G-address.'})
    amount = forms.DecimalField(min_value=0.0000001,max_value=1000000,decimal_places=7,label='Test USDC amount')
    memo = forms.CharField(max_length=28,required=False,initial='Push test payment')
    def clean_destination(self):
        value=self.cleaned_data['destination'].strip()
        if not valid_account_id(value): raise forms.ValidationError('That public Stellar address has an invalid checksum.')
        return value

class ActionForm(forms.Form):
    action = forms.ChoiceField(choices=[(x,x) for x in ['accept','fund','submit','revise','approve','dispute','cancel']])
    payment_method = forms.ChoiceField(required=False,choices=[
        ('','Choose method'),
        ('usdc','USDC simulation'),
        ('bank_card','Bank / card simulation'),
        ('stellar_usdc_testnet','Stellar USDC testnet'),
    ])
    transaction_hash = forms.RegexField(regex=r'^[0-9a-fA-F]{64}$',required=False,max_length=64)
    note = forms.CharField(required=False,max_length=500)
    accept_terms = forms.BooleanField(required=False)

class DisputeResolutionForm(forms.Form):
    resolution = forms.ChoiceField(choices=Dispute._meta.get_field('resolution').choices)
    split_percent = forms.IntegerField(required=False,min_value=1,max_value=99,label='Worker share (percent)')
    decision_note = forms.CharField(max_length=2000,widget=forms.Textarea(attrs={'rows':5}))
    def clean(self):
        data=super().clean()
        if data.get('resolution') == 'split' and data.get('split_percent') is None:
            self.add_error('split_percent','Enter the worker share for a split decision.')
        return data

class SanctionForm(forms.ModelForm):
    class Meta:
        model=AccountSanction
        fields=['kind','reason']
        widgets={'reason':forms.Textarea(attrs={'rows':4})}
