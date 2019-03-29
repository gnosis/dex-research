# dƒusion fee mechanism

## Governance mechanism fundamentals

Designing autonomous or semi-autonomous mechanisms for decentralized systems requires accommodating multiple tradeoffs under the overarching goal of ensuring ongoing operation in a trustless environment. Some objectives will be specifically defined as primary system goals, but the common objectives of security and ease of access tend to be somewhat in conflict in all systems, so a primary design principle is to right combination of the two that not just a compromise.

This section will express some design process fundamentals by which a token-based system can ensure these goals are met. It will express the fundamental paradox first and then propose a process-based method to reach viability.

### The parametrization paradox

The parametrization paradox states that a design process which tries to make an autonomous governance mechanism more responsive to the (potentially unforeseeable) state of the system will have to create more design variables which have to be parametrized. Making a governance mechanism both fully autonomous (no single participant can opportunistically interfere with the system) and fully responsive (all potential states are anticipated and mapped to valid responses) might then not be possible — It’s not just turtles all the way down, it’s a pyramid of turtles all the way down.

To design a governance mechanism then requires making tradeoffs: use simple but inflexible parameters where simplicity is required, and complex parametrizations where flexibility is required.

As a design principle, fixing parameters to a constant value is a preferable first (“minimum viable”) step as long as realistic testing is possible. Testing should hypothesize and verify failure modes of constant value parametrization before implementing more complex mechanisms.

A sequence of parametrization steps by adding complexity could look as follows. 

1. FIXED A single, invariant value x is assigned a priori to a parameter: τ = x.
2. VARIABLE The parameter is expressed as a function of state parameters: τ = f(x). The choice of the function is predefined a priori.
3. ADAPTIVE A functional form is fitted to the (history of) observed states: τ = f(x, t,...). 
4. GENERATIVE A generative algorithm anticipates resource needs and allocates resources based on the (history of) observed states: τ = τ0 iff f(x, t), τ1 else.

### Governance mechanism toolbox

Any complex governance mechanism is a combination of multiple governance modes and implementations. For instance, auctions as competitive governance modes come in multiple forms: Dutch, English, first-price, second-price, etc. Considerable effort has been put into understanding the advantages and drawbacks of each mode, but intermodal comparisons are still in their infancy.

For instance, while market vs hierarchy is a well-established intermodal comparison, it does not take into account the “enterprization” of markets which created a major impetus for the emergence of blockchain. The ability to set the rules and control the information flow creates rent extraction opportunities under non-zero exit costs.

-	**Vertical**: dictatorship, hierarchy, bureaucracy, walking away, …
-	**Competitive**: market, auction, bargaining, effort, …
-	**Participatory**: voting, consensus, ...
-	RANDOMIZED: lottery, discovery, ...

The underlying question for the choice of a governance mode is “If there are more claims for an asset than assets available, how is the order of precedence among claimants settled?” 

In decentralized systems, this is a critical question for system integrity: vertical governance modes such as dictatorial decrees leave individual discretion to the dictator and are to be avoided (the concept of “censorship resistance”). 

## Example: Proof of work and transaction validation

For instance, in proof of work censorship resistance is achieved via the combination of multiple modes. 

The right to propose a transaction blocks (mining) is conducted as a competitive auction combining competitive effort and randomized discovery: a race to be the first to discover a randomized hash which can be rigged by devoting more computational effort to it. 
The validation of blocks by nodes is a participatory consensus process: only if all nodes can agree on a invariant semi-ordering of transaction that fulfills the fundamental accounting equation (all credits are also debited) is the integrity of the system maintained. 
Even within this narrow but mission critical governance mechanism, three distinct modes (competitive, randomized, participatory) are deployed in order to avoid the fourth mode: vertical. 

## Governance mechanism design and assembly

Governance mechanisms have two primary purposes:

1. To ensure ongoing voluntary participation by all stakeholders
2. To provide the participants with the necessary incentives and safeguards to do so.

Markets are spot mechanisms. Contracts enable engagement between two or more parties over time. Especially they allow for temporary asynchronicities in control and obligations: I order, you make, you deliver, I pay. Disruptions at any juncture in such a contractual engagement can result in one party holding and keeping the assets of the other party. This is known as counterparty or expropriation risk, a form of contractual hazard.

Governance mechanisms are successful if and only if they eliminate expropriation risks at transaction costs acceptable to the participants.

### Assembly manual for governance mechanisms

-	Identify actors and their objectives
-	Identify the key interactions (“games”) 
-	Identify efforts, information flows, and payments (token transfers)
-	Formulate desired (valid) and undesired outcomes (threat models)
-	Select governance mode(s) for each interaction (market, hierarchy, participation, chance…)
-	Parametrize each interaction in the simplest possible way (“minimum viable parameters”)
-	Hypothesize on expected fail modes and intervals
-	Generate test instances and test MVP mechanism
-	Iteratively adjust parameters based on testing
