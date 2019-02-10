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

- Limited onchain storage
    - K - accounts
    - T - tokens
    - a few other constants
    - State Hash representing balances B_{k,t}

- Atomic swaps for auction settlements and other transition of account balance state


