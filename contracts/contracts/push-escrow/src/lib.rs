#![no_std]

use soroban_sdk::{
    contract, contracterror, contractevent, contractimpl, contracttype, symbol_short, token,
    Address, BytesN, Env, Symbol,
};

const AGREEMENT_TTL_THRESHOLD: u32 = 17_280;
const AGREEMENT_TTL_BUMP: u32 = 518_400;

#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub enum Status {
    Created,
    Funded,
    Submitted,
    Disputed,
    Released,
    Refunded,
    Cancelled,
    Resolved,
}

#[derive(Clone, Debug, Eq, PartialEq)]
#[contracttype]
pub struct Agreement {
    pub client: Address,
    pub worker: Address,
    pub arbiter: Address,
    pub token: Address,
    pub amount: i128,
    pub deadline: u64,
    pub review_seconds: u64,
    pub review_until: u64,
    pub revision_limit: u32,
    pub revisions: u32,
    pub status: Status,
    pub delivery_hash: Option<BytesN<32>>,
}

#[derive(Clone)]
#[contracttype]
enum DataKey {
    Agreement(BytesN<32>),
}

#[derive(Copy, Clone, Debug, Eq, PartialEq)]
#[contracterror]
#[repr(u32)]
pub enum Error {
    AlreadyExists = 1,
    NotFound = 2,
    InvalidAmount = 3,
    InvalidParties = 4,
    InvalidDeadline = 5,
    InvalidState = 6,
    InvalidSplit = 7,
    NotExpired = 8,
    Expired = 9,
}

#[contractevent]
pub struct AgreementEvent {
    #[topic]
    pub action: Symbol,
    #[topic]
    pub id: BytesN<32>,
    pub primary_amount: i128,
    pub secondary_amount: i128,
}

fn publish(env: &Env, action: Symbol, id: BytesN<32>, primary_amount: i128, secondary_amount: i128) {
    AgreementEvent { action, id, primary_amount, secondary_amount }.publish(env);
}

#[contract]
pub struct PushEscrow;

fn key(id: &BytesN<32>) -> DataKey {
    DataKey::Agreement(id.clone())
}

fn load(env: &Env, id: &BytesN<32>) -> Result<Agreement, Error> {
    let storage_key = key(id);
    let agreement = env
        .storage()
        .persistent()
        .get::<_, Agreement>(&storage_key)
        .ok_or(Error::NotFound)?;
    env.storage().persistent().extend_ttl(
        &storage_key,
        AGREEMENT_TTL_THRESHOLD,
        AGREEMENT_TTL_BUMP,
    );
    Ok(agreement)
}

fn save(env: &Env, id: &BytesN<32>, agreement: &Agreement) {
    let storage_key = key(id);
    env.storage().persistent().set(&storage_key, agreement);
    env.storage().persistent().extend_ttl(
        &storage_key,
        AGREEMENT_TTL_THRESHOLD,
        AGREEMENT_TTL_BUMP,
    );
}

fn payout(env: &Env, agreement: &Agreement, recipient: &Address, amount: i128) {
    if amount > 0 {
        token::Client::new(env, &agreement.token).transfer(
            &env.current_contract_address(),
            recipient,
            &amount,
        );
    }
}

#[contractimpl]
impl PushEscrow {
    pub fn create(
        env: Env,
        id: BytesN<32>,
        client: Address,
        worker: Address,
        arbiter: Address,
        token: Address,
        amount: i128,
        deadline: u64,
        review_seconds: u64,
        revision_limit: u32,
    ) -> Result<Agreement, Error> {
        client.require_auth();
        if env.storage().persistent().has(&key(&id)) {
            return Err(Error::AlreadyExists);
        }
        if amount <= 0 {
            return Err(Error::InvalidAmount);
        }
        if client == worker || client == arbiter || worker == arbiter {
            return Err(Error::InvalidParties);
        }
        if deadline <= env.ledger().timestamp() || review_seconds < 86_400 || review_seconds > 1_209_600 || revision_limit > 10 {
            return Err(Error::InvalidDeadline);
        }
        let agreement = Agreement {
            client,
            worker,
            arbiter,
            token,
            amount,
            deadline,
            review_seconds,
            review_until: 0,
            revision_limit,
            revisions: 0,
            status: Status::Created,
            delivery_hash: None,
        };
        save(&env, &id, &agreement);
        publish(&env, symbol_short!("created"), id, amount, 0);
        Ok(agreement)
    }

    pub fn create_fund(env: Env, id: BytesN<32>, client: Address, worker: Address,
        arbiter: Address, token: Address, amount: i128, deadline: u64,
        review_seconds: u64, revision_limit: u32) -> Result<Agreement, Error> {
        Self::create(env.clone(), id.clone(), client, worker, arbiter, token, amount,
                     deadline, review_seconds, revision_limit)?;
        Self::fund(env, id)
    }

    pub fn revise(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.client.require_auth();
        if agreement.status != Status::Submitted || agreement.revisions >= agreement.revision_limit
            || env.ledger().timestamp() > agreement.review_until { return Err(Error::InvalidState); }
        agreement.revisions += 1;
        // Each included revision receives the agreed review-window length to deliver.
        agreement.deadline = env.ledger().timestamp().checked_add(agreement.review_seconds).ok_or(Error::InvalidDeadline)?;
        agreement.review_until = 0;
        agreement.status = Status::Funded;
        save(&env, &id, &agreement);
        publish(&env, symbol_short!("revise"), id, 0, 0);
        Ok(agreement)
    }

    pub fn get(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        load(&env, &id)
    }

    pub fn fund(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.client.require_auth();
        if agreement.status != Status::Created {
            return Err(Error::InvalidState);
        }
        if env.ledger().timestamp() > agreement.deadline { return Err(Error::Expired); }
        agreement.status = Status::Funded;
        save(&env, &id, &agreement);
        token::Client::new(&env, &agreement.token).transfer(
            &agreement.client,
            &env.current_contract_address(),
            &agreement.amount,
        );
        publish(&env, symbol_short!("funded"), id, agreement.amount, 0);
        Ok(agreement)
    }

    pub fn submit(
        env: Env,
        id: BytesN<32>,
        delivery_hash: BytesN<32>,
    ) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.worker.require_auth();
        if agreement.status != Status::Funded {
            return Err(Error::InvalidState);
        }
        if env.ledger().timestamp() > agreement.deadline {
            return Err(Error::Expired);
        }
        agreement.review_until = env.ledger().timestamp().checked_add(agreement.review_seconds).ok_or(Error::InvalidDeadline)?;
        agreement.delivery_hash = Some(delivery_hash);
        agreement.status = Status::Submitted;
        save(&env, &id, &agreement);
        publish(&env, symbol_short!("submit"), id, 0, 0);
        Ok(agreement)
    }

    pub fn approve(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.client.require_auth();
        if agreement.status != Status::Submitted {
            return Err(Error::InvalidState);
        }
        agreement.status = Status::Released;
        save(&env, &id, &agreement);
        payout(&env, &agreement, &agreement.worker, agreement.amount);
        publish(&env, symbol_short!("release"), id, agreement.amount, 0);
        Ok(agreement)
    }

    pub fn cancel_unfunded(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.client.require_auth();
        if agreement.status != Status::Created {
            return Err(Error::InvalidState);
        }
        agreement.status = Status::Cancelled;
        save(&env, &id, &agreement);
        publish(&env, symbol_short!("cancel"), id, 0, 0);
        Ok(agreement)
    }

    pub fn refund_expired(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.client.require_auth();
        if agreement.status != Status::Funded {
            return Err(Error::InvalidState);
        }
        if env.ledger().timestamp() <= agreement.deadline {
            return Err(Error::NotExpired);
        }
        agreement.status = Status::Refunded;
        save(&env, &id, &agreement);
        payout(&env, &agreement, &agreement.client, agreement.amount);
        publish(&env, symbol_short!("refund"), id, agreement.amount, 0);
        Ok(agreement)
    }

    pub fn claim_expired(env: Env, id: BytesN<32>) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.worker.require_auth();
        if agreement.status != Status::Submitted {
            return Err(Error::InvalidState);
        }
        if env.ledger().timestamp() <= agreement.review_until {
            return Err(Error::NotExpired);
        }
        agreement.status = Status::Released;
        save(&env, &id, &agreement);
        payout(&env, &agreement, &agreement.worker, agreement.amount);
        publish(&env, symbol_short!("claim"), id, agreement.amount, 0);
        Ok(agreement)
    }

    pub fn open_dispute(
        env: Env,
        id: BytesN<32>,
        caller: Address,
    ) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        caller.require_auth();
        if caller != agreement.client && caller != agreement.worker {
            return Err(Error::InvalidParties);
        }
        if agreement.status != Status::Funded && agreement.status != Status::Submitted {
            return Err(Error::InvalidState);
        }
        agreement.status = Status::Disputed;
        save(&env, &id, &agreement);
        publish(&env, symbol_short!("dispute"), id, 0, 0);
        Ok(agreement)
    }

    pub fn resolve(
        env: Env,
        id: BytesN<32>,
        client_amount: i128,
        worker_amount: i128,
    ) -> Result<Agreement, Error> {
        let mut agreement = load(&env, &id)?;
        agreement.arbiter.require_auth();
        if agreement.status != Status::Disputed {
            return Err(Error::InvalidState);
        }
        if client_amount < 0
            || worker_amount < 0
            || client_amount.checked_add(worker_amount) != Some(agreement.amount)
        {
            return Err(Error::InvalidSplit);
        }
        agreement.status = Status::Resolved;
        save(&env, &id, &agreement);
        payout(&env, &agreement, &agreement.client, client_amount);
        payout(&env, &agreement, &agreement.worker, worker_amount);
        publish(&env, symbol_short!("resolve"), id, client_amount, worker_amount);
        Ok(agreement)
    }
}

mod test;
