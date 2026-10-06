from types import SimpleNamespace as Obj
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from stellar_sdk import Keypair, TransactionEnvelope
from .models import User, StaffAccess, EscrowStaffWallet, EscrowStaffOperation, Payment
from .escrow_staff import permission
from .escrow_policy import can_review
from .escrow import NETWORK
from .stellar import StellarVerificationError
from .views import TERMS_VERSION


class StaffWalletTests(TestCase):
    def setUp(self):
        self.signer=Keypair.random()
        self.owner=self.person('owner','owner')
        self.admin=self.person('admin','admin')
        self.support=self.person('support','trust_support')
        self.member=self.person('member',None)

    def person(self,name,role):
        user=User.objects.create_user(username=name,email=name+'@test.example',email_verified=True,
            terms_version=TERMS_VERSION,terms_accepted_at=timezone.now())
        if role: StaffAccess.objects.create(user=user,role=role,status='approved')
        return user

    def proof(self,user,signer):
        self.client.force_login(user)
        response=self.client.post(reverse('escrow_staff_prepare'),{'action':'prove','wallet':signer.public_key},content_type='application/json')
        self.assertEqual(response.status_code,200,response.content)
        data=response.json(); tx=TransactionEnvelope.from_xdr(data['xdr'],NETWORK);tx.sign(signer)
        return data,tx

    @patch('core.escrow_staff.chain.server')
    def test_proof_registers_once_and_is_never_broadcast(self,server):
        data,tx=self.proof(self.support,self.signer)
        self.assertEqual(tx.transaction.sequence,0)
        url=reverse('escrow_staff_submit');body={'token':data['token'],'signedXdr':tx.to_xdr()}
        self.assertEqual(self.client.post(url,body,content_type='application/json').status_code,200)
        self.assertEqual(self.client.post(url,body,content_type='application/json').status_code,200)
        self.assertEqual(EscrowStaffWallet.objects.get(user=self.support).address,self.signer.public_key)
        self.assertEqual(EscrowStaffWallet.objects.count(),1);server.assert_not_called()

    def test_forged_proof_wrong_account_and_expiry_rejected(self):
        data,tx=self.proof(self.support,self.signer);url=reverse('escrow_staff_submit')
        unsigned=TransactionEnvelope.from_xdr(data['xdr'],NETWORK);unsigned.sign(Keypair.random())
        self.assertEqual(self.client.post(url,{'token':data['token'],'signedXdr':unsigned.to_xdr()},content_type='application/json').status_code,400)
        self.client.force_login(self.admin)
        self.assertNotEqual(self.client.post(url,{'token':data['token'],'signedXdr':tx.to_xdr()},content_type='application/json').status_code,200)
        self.client.force_login(self.support)
        from datetime import timedelta
        EscrowStaffOperation.objects.filter(pk=data['token']).update(created_at=timezone.now()-timedelta(minutes=6))
        self.assertEqual(self.client.post(url,{'token':data['token'],'signedXdr':tx.to_xdr()},content_type='application/json').status_code,400)
        self.assertFalse(EscrowStaffWallet.objects.exists())

    def test_ordinary_member_cannot_register_or_manage(self):
        self.client.force_login(self.member)
        self.assertEqual(self.client.get(reverse('escrow_staff')).status_code,403)
        self.assertEqual(self.client.post(reverse('escrow_staff_prepare'),{'action':'prove','wallet':self.signer.public_key},content_type='application/json').status_code,403)

    def test_role_hierarchy_and_self_grants(self):
        permission(self.owner,self.admin,2);permission(self.admin,self.support,1)
        for actor,target,role in [(self.support,self.admin,2),(self.admin,self.owner,0),(self.admin,self.member,2),(self.owner,self.owner,2),(self.owner,self.member,1)]:
            with self.assertRaises(StellarVerificationError):permission(actor,target,role)

    def test_all_verified_staff_can_review_but_not_participants_or_revoked(self):
        agreement=Obj(staff_governed=True,assignment=Obj(job=Obj(owner_id=900),worker_id=901),client_address='client',worker_address='worker')
        for user in (self.owner,self.admin,self.support):
            EscrowStaffWallet.objects.create(user=user,address=Keypair.random().public_key)
            self.assertTrue(can_review(user,agreement))
        agreement.assignment.worker_id=self.admin.pk;self.assertFalse(can_review(self.admin,agreement))
        self.support.staff_access.status='revoked';self.support.staff_access.save()
        self.assertFalse(can_review(self.support,agreement))
        self.assertFalse(can_review(self.member,agreement))

    def test_duplicate_wallet_cannot_be_assigned_to_another_staff_account(self):
        EscrowStaffWallet.objects.create(user=self.owner,address=self.signer.public_key)
        self.client.force_login(self.support)
        response=self.client.post(reverse('escrow_staff_prepare'),{'action':'prove','wallet':self.signer.public_key},content_type='application/json')
        self.assertEqual(response.status_code,400)

    def test_staff_screen_renders_without_contract_activation(self):
        self.client.force_login(self.support)
        response=self.client.get(reverse('escrow_staff'))
        self.assertContains(response,'Verify my wallet in Freighter')
        self.assertContains(response,'has not been activated')

    def test_admin_cannot_demote_an_owner_to_bypass_role_protection(self):
        self.client.force_login(self.admin)
        response=self.client.post(reverse('staff_team'),{'email':self.owner.email,'role':'trust_support'})
        self.owner.staff_access.refresh_from_db()
        self.assertEqual(self.owner.staff_access.role,'owner')


class TestnetOnlyTests(TestCase):
    def setUp(self):
        self.owner=User.objects.create_user(username='client',email='client@test.example',email_verified=True,terms_version=TERMS_VERSION,terms_accepted_at=timezone.now())
        self.worker=User.objects.create_user(username='worker',email='worker@test.example',email_verified=True,terms_version=TERMS_VERSION,terms_accepted_at=timezone.now())
        from .models import Job,Assignment
        from datetime import timedelta
        self.job=Job.objects.create(owner=self.owner,title='Test',budget=10,deadline=timezone.localdate()+timedelta(days=10))
        self.item=Assignment.objects.create(job=self.job,worker=self.worker,budget=10,scope='Test',escrow_required=False)
        self.client.force_login(self.owner)

    def test_simulated_actions_are_blocked_and_unpaid_conversion_requires_confirmation(self):
        url=reverse('assignment_action',args=[self.item.pk])
        for action in ('fund','approve','release','accept','convert_escrow'):
            self.assertEqual(self.client.post(url,{'action':action,'payment_method':'simulation'}).status_code,400)
        self.assertFalse(Payment.objects.exists())
        response=self.client.post(url,{'action':'convert_escrow','confirm_unpaid':'on'})
        self.assertEqual(response.status_code,302)
        self.item.refresh_from_db();self.assertTrue(self.item.escrow_required);self.assertEqual(self.item.status,'awaiting_acceptance')

    def test_completed_simulation_is_preserved_not_converted(self):
        Payment.objects.create(assignment=self.item,amount=10,method='simulation',simulated=True)
        response=self.client.post(reverse('assignment_action',args=[self.item.pk]),{'action':'convert_escrow','confirm_unpaid':'on'})
        self.assertEqual(response.status_code,400);self.assertEqual(Payment.objects.count(),1)
        self.item.refresh_from_db();self.assertFalse(self.item.escrow_required)

    @patch('core.views.submit_signed_payment')
    def test_retired_direct_endpoint_never_broadcasts(self,broadcast):
        response=self.client.post(reverse('wallet_submit'),{'signedXdr':'old request'},content_type='application/json')
        self.assertEqual(response.status_code,409);broadcast.assert_not_called()

    def test_historical_simulation_is_excluded_from_confirmed_totals(self):
        Payment.objects.create(assignment=self.item,amount=10,method='simulation',simulated=True)
        self.client.force_login(self.worker)
        response=self.client.get(reverse('payments'))
        self.assertEqual(response.context['total_earnings'],0)
        self.assertEqual(response.context['pending_earnings'],0)


from django.test import TransactionTestCase, skipUnlessDBFeature

@override_settings(PUSH_TESTNET_ESCROW_ENABLED=True,PUSH_TESTNET_ESCROW_CONTRACT='Ctest')
class EscrowConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature('has_select_for_update')
    @patch('core.escrow.build')
    def test_concurrent_funding_requests_prepare_only_one_transaction(self,build):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections, connections
        from django.test import Client
        from datetime import timedelta
        from stellar_sdk import Account, TransactionBuilder
        from .models import Job,Assignment,EscrowAgreement,EscrowTransaction
        signer=Keypair.random()
        attrs={'email_verified':True,'terms_version':TERMS_VERSION,'terms_accepted_at':timezone.now()}
        client=User.objects.create_user(username='concurrent-client',email='client@concurrent.test',stellar_address=signer.public_key,**attrs)
        worker=User.objects.create_user(username='concurrent-worker',email='worker@concurrent.test',**attrs)
        reviewer=User.objects.create_user(username='concurrent-reviewer',email='reviewer@concurrent.test',**attrs)
        job=Job.objects.create(owner=client,title='Concurrency',budget=1,deadline=timezone.localdate()+timedelta(days=2))
        item=Assignment.objects.create(job=job,worker=worker,budget=1,escrow_required=True,status='awaiting_funding')
        EscrowAgreement.objects.create(assignment=item,reviewer=reviewer,contract='Ctest',agreement_id='f'*64,client_address=signer.public_key,worker_address='worker',reviewer_address='reviewer',asset='XLM',token_address='token',amount=1,deadline=9999999999,review_seconds=86400,revision_limit=1,accepted_at=timezone.now())
        build.return_value=TransactionBuilder(Account(signer.public_key,1),NETWORK,100).append_manage_data_op('test','test').set_timeout(300).build()
        ready=Barrier(2)
        def request():
            close_old_connections()
            try:
                c=Client();c.force_login(User.objects.get(pk=client.pk));session=c.session;session['wallet_connected_address']=signer.public_key;session.save()
                ready.wait(timeout=10)
                return c.post(reverse('escrow_prepare',args=[item.pk]),{'action':'fund'},content_type='application/json').status_code
            finally: connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as executor:
            results=list(executor.map(lambda _:request(),range(2)))
        self.assertEqual(sorted(results),[200,400])
        self.assertEqual(EscrowTransaction.objects.count(),1);self.assertEqual(build.call_count,1)
