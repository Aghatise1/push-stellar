#![cfg(test)]

use super::*;
use soroban_sdk::{
    testutils::{Address as _, Ledger},
    token, Address, BytesN, Env,
};

fn setup() -> (Env, Address, Address, Address, Address, Address) {
    let env = Env::default();
    env.mock_all_auths();
    env.ledger().set_timestamp(1_000);
    let client = Address::generate(&env);
    let worker = Address::generate(&env);
    let arbiter = Address::generate(&env);
    let asset_admin = Address::generate(&env);
    let token = env.register_stellar_asset_contract_v2(asset_admin).address();
    let contract = env.register(PushEscrow, ());
    token::StellarAssetClient::new(&env, &token).mint(&client, &10_000);
    (env, client, worker, arbiter, token, contract)
}

fn id(env: &Env, byte: u8) -> BytesN<32> {
    BytesN::from_array(env, &[byte; 32])
}

fn create_and_fund(
    env: &Env,
    contract_address: &Address,
    agreement_id: &BytesN<32>,
    client: &Address,
    worker: &Address,
    arbiter: &Address,
    token: &Address,
    deadline: u64,
) {
    let contract = PushEscrowClient::new(env, contract_address);
    contract.create(
        agreement_id,
        client,
        worker,
        arbiter,
        token,
        &1_000,
        &deadline,
        &86_400,
        &2,
    );
    contract.fund(agreement_id);
}

#[test]
fn funding_and_approval_release_the_exact_amount() {
    let (env, client, worker, arbiter, token, contract_address) = setup();
    let agreement_id = id(&env, 1);
    create_and_fund(&env, &contract_address, &agreement_id, &client, &worker, &arbiter, &token, 2_000);
    let token_client = token::Client::new(&env, &token);
    assert_eq!(token_client.balance(&client), 9_000);
    assert_eq!(token_client.balance(&contract_address), 1_000);
    let contract = PushEscrowClient::new(&env, &contract_address);
    contract.submit(&agreement_id, &id(&env, 9));
    let agreement = contract.approve(&agreement_id);
    assert_eq!(agreement.status, Status::Released);
    assert_eq!(token_client.balance(&worker), 1_000);
    assert_eq!(token_client.balance(&contract_address), 0);
}

#[test]
fn client_can_refund_only_after_an_unsubmitted_deadline() {
    let (env, client, worker, arbiter, token, contract_address) = setup();
    let agreement_id = id(&env, 2);
    create_and_fund(&env, &contract_address, &agreement_id, &client, &worker, &arbiter, &token, 2_000);
    let contract = PushEscrowClient::new(&env, &contract_address);
    assert!(contract.try_refund_expired(&agreement_id).is_err());
    env.ledger().set_timestamp(2_001);
    let agreement = contract.refund_expired(&agreement_id);
    assert_eq!(agreement.status, Status::Refunded);
    assert_eq!(token::Client::new(&env, &token).balance(&client), 10_000);
}

#[test]
fn worker_can_claim_submitted_work_after_deadline() {
    let (env, client, worker, arbiter, token, contract_address) = setup();
    let agreement_id = id(&env, 3);
    create_and_fund(&env, &contract_address, &agreement_id, &client, &worker, &arbiter, &token, 2_000);
    let contract = PushEscrowClient::new(&env, &contract_address);
    contract.submit(&agreement_id, &id(&env, 8));
    env.ledger().set_timestamp(87_401);
    let agreement = contract.claim_expired(&agreement_id);
    assert_eq!(agreement.status, Status::Released);
    assert_eq!(token::Client::new(&env, &token).balance(&worker), 1_000);
}

#[test]
fn worker_cannot_submit_after_the_deadline() {
    let (env, client, worker, arbiter, token, contract_address) = setup();
    let agreement_id = id(&env, 6);
    create_and_fund(&env, &contract_address, &agreement_id, &client, &worker, &arbiter, &token, 2_000);
    env.ledger().set_timestamp(2_001);
    let contract = PushEscrowClient::new(&env, &contract_address);
    assert!(contract.try_submit(&agreement_id, &id(&env, 6)).is_err());
    assert_eq!(contract.get(&agreement_id).status, Status::Funded);
}

#[test]
fn arbiter_can_split_a_disputed_payment_without_creating_value() {
    let (env, client, worker, arbiter, token, contract_address) = setup();
    let agreement_id = id(&env, 4);
    create_and_fund(&env, &contract_address, &agreement_id, &client, &worker, &arbiter, &token, 2_000);
    let contract = PushEscrowClient::new(&env, &contract_address);
    contract.open_dispute(&agreement_id, &worker);
    assert!(contract.try_resolve(&agreement_id, &500, &600).is_err());
    let agreement = contract.resolve(&agreement_id, &350, &650);
    assert_eq!(agreement.status, Status::Resolved);
    let token_client = token::Client::new(&env, &token);
    assert_eq!(token_client.balance(&client), 9_350);
    assert_eq!(token_client.balance(&worker), 650);
    assert_eq!(token_client.balance(&contract_address), 0);
}

#[test]
fn completed_agreement_cannot_pay_twice() {
    let (env, client, worker, arbiter, token, contract_address) = setup();
    let agreement_id = id(&env, 5);
    create_and_fund(&env, &contract_address, &agreement_id, &client, &worker, &arbiter, &token, 2_000);
    let contract = PushEscrowClient::new(&env, &contract_address);
    contract.submit(&agreement_id, &id(&env, 7));
    contract.approve(&agreement_id);
    assert!(contract.try_approve(&agreement_id).is_err());
    assert_eq!(token::Client::new(&env, &token).balance(&worker), 1_000);
}

#[test]
fn review_window_starts_at_submission_not_delivery_deadline() {
    let (env, client, worker, arbiter, token, address) = setup();
    let key=id(&env,10);
    create_and_fund(&env,&address,&key,&client,&worker,&arbiter,&token,2_000);
    env.ledger().set_timestamp(1_999);
    let contract=PushEscrowClient::new(&env,&address);
    contract.submit(&key,&id(&env,11));
    env.ledger().set_timestamp(2_001);
    assert!(contract.try_claim_expired(&key).is_err());
    assert!(contract.try_refund_expired(&key).is_err());
    assert_eq!(contract.get(&key).review_until,88_399);
}

#[test]
fn atomic_funding_rolls_back_when_balance_is_insufficient() {
    let (env,client,worker,arbiter,token,address)=setup();
    let contract=PushEscrowClient::new(&env,&address);
    let key=id(&env,12);
    assert!(contract.try_create_fund(&key,&client,&worker,&arbiter,&token,&20_000,&2_000,&86_400,&2).is_err());
    assert!(contract.try_get(&key).is_err());
    assert_eq!(token::Client::new(&env,&token).balance(&client),10_000);
}

#[test]
fn revisions_are_bounded_and_give_worker_a_new_delivery_window() {
    let (env,client,worker,arbiter,token,address)=setup();
    let contract=PushEscrowClient::new(&env,&address);let key=id(&env,13);
    contract.create_fund(&key,&client,&worker,&arbiter,&token,&1_000,&2_000,&86_400,&1);
    contract.submit(&key,&id(&env,14));
    env.ledger().set_timestamp(3_000);
    let revised=contract.revise(&key);
    assert_eq!(revised.deadline,89_400);assert_eq!(revised.revisions,1);
    contract.submit(&key,&id(&env,15));
    assert!(contract.try_revise(&key).is_err());
}

#[test]
fn missing_client_authorisation_cannot_release_funds() {
    let (env,client,worker,arbiter,token,address)=setup();
    let key=id(&env,16);create_and_fund(&env,&address,&key,&client,&worker,&arbiter,&token,2_000);
    let contract=PushEscrowClient::new(&env,&address);contract.submit(&key,&id(&env,17));
    env.mock_auths(&[]);
    assert!(contract.try_approve(&key).is_err());
    assert_eq!(token::Client::new(&env,&token).balance(&address),1_000);
}

#[test]
fn dispute_blocks_release_and_expiry_paths() {
    let (env,client,worker,arbiter,token,address)=setup();
    let key=id(&env,18);create_and_fund(&env,&address,&key,&client,&worker,&arbiter,&token,2_000);
    let contract=PushEscrowClient::new(&env,&address);contract.submit(&key,&id(&env,19));
    contract.open_dispute(&key,&client);env.ledger().set_timestamp(100_000);
    assert!(contract.try_approve(&key).is_err());assert!(contract.try_claim_expired(&key).is_err());assert!(contract.try_refund_expired(&key).is_err());
}
