dFusion
=======

Decentralized Multi-Token Batch Auction Exchange Mechanism as a Snark-Application

- Limit orders between any token paris collected in a batch (over three minutes or upto N orders)
    - N is dictated by the size of snarks

- Price finding / order matching algorithm is modeled as a Mixed Integer Program whose 
    
    Objective Function; 

        - Trader's Welfare/surplus

    Feasibility Region; 
        
        - Respected Limit Prices
        - Conservation of Value [ No tokens are created or destroyed during a settlement ]
        - Price Coherence [ p_ij * p_ji = 1 ]
        - Arbitrage Freeness [ prices along cycles multiply to 1 ]

Benifits;
    
    Ring Trades; 
        Faciliates higher likelyhood or order fulfillment
    Fair by design; 
        As defined by the feasible region




Decentralization achieved by
----------------------------

- Anyone can submit solution proposals to auction results 
    - Smart Contract will choose the best
    - reward mechanism in place for best solution
    - Winning solution will be expected to provide Snark Proof (Proof of Optimization)

- Anyone can propose state transition
- State transitions can be Challenged


Scalability achieved by
-----------------------

1. Limited onchain storage
    - K - accounts
    - T - tokens
    - a few other constants
    - State Hash representing balances B_{k,t}

2. Atomic swaps for auction settlements and other transition of account balance state


3. SNARKS (Succinct Non-interactive ARguments of Knowledge)
    
    - Prover (Solution Proposer) does a lot of computation off-chain [more than necessary] to prove that a computation was executed correctly to generate an easily verifiable proof which is submitted on-chain in the form of a smart contract
    - In terms of complexity, An O(n) algorithm can be proven to have been statistically executed correctly with O(n^3) and generates a proof that can be verified in O(1) [The O(1) proof is on-chain while the O(n^3) generation is left off]

    - We use snarks in three different places. Namely for any transition of account balances.
        - Processing Deposits
        - Processing Withdrawals
        - Auction Settlement

Backing up

Snark Applications (SNAPPS)
---------------------------


- Contract;

    - registerAccount

    - deposit, processDeposits
    - requestWithdraw, processWithdraws

    - challangeState, submitProof, rollBack

    - applicationSpecificStateChangingFunction (placeOrder, applyAuction)

Upcomming Challanges
--------------------

- Forkable States
- Batch Requests i.e. Off-Chain Order Collectors (as a service) 
    (depoist, withdraw, limitOrder) 
    for batch transactions 
    (batchDeposit, batchWithdrawRequest, batchOrder)



Summary
-------
In summary, snark application enables us to 

Requests (Emit Events)
    - deposit - "Account k Deposited d of token t"
    - withdraw - "Account k Withdrew d of token t"
    - limitOrder - "Account k wants to trade at most d of token i for token j if the exchange rate is at most r"

Contract doesn't store the information contained in events.
Off-chain Event Listeners are in place collecting and storing this information (Anyone can listen)
When time is right, this information can be used to "Drive" the contract (i.e. update Account states)



ProcessRequests (AccountStateTransitions)
    - deposits & withdrawals  
        (snark contains all information regarding deposits in that slot)
    - applyAuction 
        (Snark contains, prices and limit-order fulfullment is sufficient to demonstrate constraints of Linear Program)


    






