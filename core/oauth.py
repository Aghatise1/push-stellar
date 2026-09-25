from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
import sys


class PushSocialAccountAdapter(DefaultSocialAccountAdapter):
    """Map trusted provider identity into Push's profile fields."""

    @staticmethod
    def provider_verified_email(sociallogin):
        data = sociallogin.account.extra_data or {}
        return sociallogin.account.provider == 'google' and data.get('email_verified') is True

    def populate_user(self, request, sociallogin, data):
        user = super().populate_user(request, sociallogin, data)
        candidate = (data.get('name') or data.get('email', '').split('@')[0] or 'Push member').strip()
        user.display_name = candidate[:80]
        if self.provider_verified_email(sociallogin):
            user.email_verified = True
        return user

    def pre_social_login(self, request, sociallogin):
        super().pre_social_login(request, sociallogin)
        if sociallogin.is_existing and self.provider_verified_email(sociallogin):
            type(sociallogin.user).objects.filter(pk=sociallogin.user.pk,email_verified=False).update(email_verified=True)
            sociallogin.user.email_verified = True

    def save_user(self, request, sociallogin, form=None):
        user = super().save_user(request, sociallogin, form)
        user.email_verified = self.provider_verified_email(sociallogin)
        if not user.display_name:
            user.display_name = (user.email.split('@')[0] or 'Push member')[:80]
        user.save(update_fields=['display_name','email_verified'])
        return user

    def on_authentication_error(self, request, provider, error=None, exception=None, extra_context=None):
        # Log only the category. Provider responses can contain credentials and
        # must never be written to the console or shown to the visitor.
        exception_name = type(exception).__name__ if exception is not None else 'None'
        print(
            f'Push social authentication failed: provider={provider.id} '
            f'error={error or "unspecified"} exception={exception_name}',
            file=sys.stderr,
            flush=True,
        )
        return super().on_authentication_error(
            request,
            provider,
            error=error,
            exception=exception,
            extra_context=extra_context,
        )
