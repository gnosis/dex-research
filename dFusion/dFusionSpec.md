# dFusion - decentralized scalable onchain exchange



A specification developed by Gnosis.


The following specification uses the snark application (snapp) onchain scaling approach, in order to build a scalable fully decentralized exchange with decentralized order matching. 
The scalability is enabled storing information only in hashes and allow snarks the manipulation of these hashes in predefined logic gates [[link](https://ethresear.ch/t/on-chain-scaling-to-potentially-500-tx-sec-through-mass-tx-validation/3477)].
Orders are matched in a batch auction with an arbitrage-free price clearing technique developed by Gnosis: [Uniform Clearing Prices]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf).

## Summary
The envisioned exchange will enable `K` accounts to trade via limit orders between `N` predefined ERC20 tokens.
Limit orders are collected and matched in batches, with each batch containing up to `M` orders. 
Orders within a batch can be matched directly (e.g. an order trading token A for B against another order trading token B for A) or in arbitrarily long "ringtrades" (e.g. an order trading token A for B, with another one trading token B for C, with a third one trading token C for A).

The matching process is decentralized.
After orders have been collected over a certain amount of time, a batch is frozen and any sufficiently bonded participant can suggest a matching of orders in the current batch.

If more than one solution is submitted within a certain amount of time after the batch closes, the one that generates the largest "trader surplus" (detailed explanation below, for now think "trading volume") is selected and executed.
For this, the "winner" has to post enough information about the solution on-chain, so that any participant can quickly check the validity of the solution.

Anyone can challenge a solution on-chain (while providing a bond and an alternative solution) within a certain time-period after posting.
Such disputes are resolved by verifying a zkSnark proof on-chain that checks if the provided solution fulfills a number of constraints (specified in detail below).
If the verification succeeds, the challenger loses their bond and the state is "finalized". 
If the verification fails the provided alternative state is assumed correct unless challenged within a certain time.

## State stored in the smart contract

For each account, we chain each of ERC20 token balance together and store them as pedersen hash (not merkleized) in the anchor smart contract.
This "compressed" representation of all account balances is collision resistant and can thus be used  which will store all relevant information for this snapp exchange.
The following diagram shows the state construction:

![State construction](./dFusion%20rootHash.png?raw=true "State construction")

To allow `K` to be small, a bi-map of an accounts public key (on-chain address) to its `accountIndex` will be stored in the anchor contract as well. 
Accounts will pay "rent" to occupy an active account. The account index can be used to locate a users token balances in the state.

Furthermore, we store a bi-map of token address to its index `0 <= n <= N`, for each token that can be traded on the exchange.
When specifying tokens inside orders, deposits and withdrawel requests, we use the token's index `0 <= n <= N` instead of the full address.

As orders, deposits and withdrawl requests are collected they are not directly stored in the smart contract.
Doing so would require a `SSTORE` instruction which would be too gas-expensive.
Assuming an order can be encoded in 256 bits, storing a batch of 10.000 on chain would cost ~5M gas (5.000 gas for SSTORE * 10.000 orders).
Instead the smart contract emits a smart contract event containing the relevant order information (account, from_token, to_token, limit) and stores a rolling SHA hash.
For a new order, the rolling hash is computed by hashing the previous rolling hash with the current order.

// TODO: Pending withdrawels

## Batch Auction Workflow

The trading workflow consists of the following sequential processes:
0. Account opening, deposits & withdrawels
1. On-Chain order collection
2. Transition function from sha to Pedersen hashes (zkSnark)
3. Finding the batch price: optimization of batch trading surplus (offchain)
4. Verifying batch price and trade execution (zkSnark)
5. Processing of pending exits and deposits (zkSnark)
6. Restart with step 0

### Account opening, deposits & withdrawels

// TODO

### On-Chain order collection

All orders are encoded as limit sell orders: `(accountIndex, fromTokenIndex, toTokenIndex, limitPrice, amount, batchId, signature)`.
The order should be read in the following way: the user occupying the specified *accountIndex* would like to sell the token *fromTokenIndex* for *toTokenIndex* for at most the *limitPrice* and the *amount* specified.
The *batchId* and *signature* allow a third party to submit an order on behalf of others (saving gas when batching multiple orders together).
The user only has to specify which batch their order is valid for and sign all the information with their private key.

The anchor smart contract on ethereum will offer the following function:
```js
function appendOrders( bytes32 [] orders){ 
	// some preliminary checks limiting the number of orders..

	// update of orderHashSha
	for(i=0; i<orders.length; i++){
		if("check signature and batchID of order") {
			// hash order without signature
			orderHashSha = Kecca256(orderHashSha, orders[i]) 
		}
	}
}
```
This function will simply update an orderHashSha variable, which is chaining all orders with a valid signature. This function is callable by any party. However, it is expected that “decentralized operators” accept orders from users, bundle them and then include them all together into the function. 

Notice, that the orders are only sent over as transaction payload, but will not be “stored” in the EVM.

Also notice, that we allow orders, which might not be covered by any balance of the order sender. These orders will be sorted out later in the settlement of an auction.

### Transition function from sha to Pedersen hashes (zkSnark)

In the first step, the orders are hashed together using SHA256 since this is very cheap on the EVM. However, SHA256 is very “expensive” in snarks. We therefore translate the resulting orderHash into a pedersen hash after order collection for a batch has finished. 

We will use a snark to do this job:
```
Snark - TransitionHashes&Validation ( public input: orderHashSha,
					Private input: [orders])
					Output: orderHashPedersen
```
The transitionHashes&Validation snark will do the following checks:
- Verify the private input by recalculating SHA256 of all orders and comparing it to the public input `orderHashSha`.
- Iterate over all orders again and hash them sequencially using the Pedersen hash. Use this hash as output.

Since computing the actual snark proof is very time-intense we optimistically accept state transitions that provide a significant bond instead of the actual proof.

Anyone can propose a transition to the anchor contract by providing the required information:

```js
Function submitTransitionInformation(uint branchId, bytes32 orderHashPedersen)
```

In case the information is incorrect, anyone can challenge it by also providing a significant bond and calling the following function.

```js
Function challengeTransitionInformation(bytes32 orderHashPedersen)
```
Any significantly bonded challenge is, by default, assumed to be legitimate and will be executed after a certain time frame (some hours), unless the first transition submitter can provide a snark proof of correctness within this predefined time frame.

The snark will be evaluated by the anchor contract after calling the following function. The contract will populate public inputs and outputs to the snark with the data from the challenged submission.
 ```js
Function submitSnarkToResolveChallenge(branchId, --snark--)
```

During the challenge period, multiple "forks" of the state will be stored (one for each submitted solution). . While producing a snark proof takes a lot of time, executing the computation in a native program on a local computer is fast. Therefore any client should be able to "predict", which challenges will be successful and can thus chose on which fork they want to continue trading.

### Finding the batch price: optimization of batch trading surplus (offchain)

After the previous step, the orders participating in a batch have finalized. Now, the uniform clearing price maximizing the trading surplus between all trading pairs can be calculated. The traders surplus of one order is the difference between the uniform clearning price and the limit price, multipied by the volume of the order with respect to some reference token. The exact procedure is described [here]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf). Calculating the uniform clearing prices is an np hard optimization problem and most likely the global optimum will not be found in the pre-defined short time frame: `SolvingTime` - we think that 3-10 minutes are reasonable. While it is a pity that the global optimum cannot be found, the procedure is still fair, as everyone can submit their best solution. The anchor contract will store all submissions and will select the solution with the maximal 'traders surplus' as the final solution. We define the traders surplus as the sum of all differences between the uniform clearning prices and the limit price of an touched order multiplied by the surplus of the order.

This means the uniform clearing price of the auction is calculated in a permission-less decentralized way.	
Each time a solution is submitted to the anchor contract, of course, the submitter also needs to bond himself. If he provides the solution, he also has to provide in the next process step the balance update information and has to answer any challenge request.


### Verifying batch price and trade execution (zkSnark)


After the price submission period, the best solution with the highest trading surplus will be chosen by the anchor contract. The submitter of this solution needs to do 2 steps:

1) posting the full solution into the ethereum chain as payload. The solution is a price vector P, a new stateHash with the updated account balances, a vector of trading surpluss (VV) for each order.

| P | Token_1:Token_1 | ... | Token_N:Token_1|
| --- | --- | --- | --- | 
| price | p_1 | ... | p_N |


`P` is only the price vector of all prices relative to a reference token `Token_1`. As prices are arbitrage-free, we can calculate the `price Token_i: Token_k` =  `(Token_i:Token_1):(Token_1:Token_k)`

Unfortunately, not all orders below the limit price will be filled completely. It might happen that the account sending the order might not have the balance required to settle the sell order. We are calling these "uncovered orders" and they need to be excluded or only partly be filled. Because of this, the solution submitter must provide the fraction of the traded surplus for each order:

| VV | order_1 | ... | order_K|
| --- | --- | --- | --- |
| fraction | o_1 | --- | o_K |



These two parts of the solution: VV and P are provided as data payload to the anchor contract which will sha-hash them together into `hashBatchInfo`.

Now, everyone can check whether the provided solution is actually a valid one. If it is not valid, then anyone can challenge the solution submitter. If this happens, the solution submitter needs to prove that his solution is correct by providing the following snark:
```
Snark - applyAuction(
	Public: state,
	Public: tradingWelfare,
	Public: hashBatchInfo,
	Public: orderHashPedersen,
	Private: priceMatrix PxP,
	Private: volumeVector
	Private: balances
	Private: orders,
	Output: newstate
)
```
The snark would check the following things:

- `priceMatrix` has actually the values as induced by the `hashBatchInfo` (with sha)
- `orderVolume` VV has actually the values induced by the `hashBatchInfo` (with sha)
- verify `[tok_j_i for 0<j<K & 0<i<=N]` hashes to `state` (with pedersen)

- let `currentOrderHash = 0`
- for order in [orders]
	- read the potentially fractional surplus of the order
	- update the balance by subtracting sell volume
	- update the balance by adding buy volume
	- Keep track of the total `selling surplus` per token
	- Keep track of the total `buying surplus` per token
	- Keep track of the total `selling volume` per token
	- Keep track of the total `buying volume ` per token
	- update `currentOrderHash = hash(currentOrderHash, order)` (with pedersen)
	
- For all token, check that `selling volume == buying volume`
- Check that `selling surplus + buying surplus == tradingWelfare`
- Check that `currentOrderHash == orderHashPedersen`
- For all balances, check that `balance > 0` and calculate/return `newstate`

### Processing of pending exits and deposits (zkSnark)

Deposits and withdraws need to be processed and incorporated into the 'stateHash' as well. For this, we make again use of snarks and specific challenging periods.

In order to deposit funds into the exchange, one would send funds into the following function of the anchor contract:

```js
Function deposit ( address token, uint amount){
	// verify that not too much deposits have already been done,

	// sending of funds
	require( Token(token).transferFrom(...))
	
	uint accountIndex = ... //lookup accountIndex from msg.sender

	// Storing deposit information
	depositHash[blocknr/20] = sha256(depositHash[blocknr/20], accountIndex, amount, token) 
}
```

That means that all the depositing information are stored in a bytes32 `depositHash`. Each 20 ethereum blocks, we store all the occurring `depositsHash` in a unique hash.

The deposits can be incorporated by any significantly bonded party by calling the following function:
```js
Function incorporateDeposits(uint blockNr, bytes32 newState)
```
This function would update the `state` by incorporating the deposits received from `blockNr` to `blockNr+19`.

Everyone can check whether the `stateRH` has been updated correctly. If it has not been updated correctly, then the person submitting this solution can be challenged by providing a bond.

To resolve the challenge one must provide the following snark:

```
snark-deposits( 
		Public: oldState
		Public: depositHash
		Private: [deposit informations]
		Private: [old balances] 
		Output: newState
)
```	

This snark would check that:

- By SHA256 hashing the `[deposit information]`, we are getting the `depositHash`
- Calculate the stateHash based on current balances and make sure it matches input
- for( deposits in `[deposit information]`)
	- Update the leaf with the current balance,
- Recalculate the stateHash based on updated balances
		

Something quite similar will be done with exit requests. If a user wants to exit, they first need to do an exit request by calling the following function in the anchor contract:

```js
Function exitRequest ( address token, uint amount){
	// verify that not too much exists request have already been done,

	uint accountIndex = ... //lookup accountIndex from msg.sender
	
	// Storing deposit information
	exitRequestHash[blocknr/20] = sha256(exitRequestHash[blocknr/20], accountIndex, amount, token) 
}
```

Then any significantly bonded party can incorporate these bundled exit requests into the current stateRH by calling the following function:

```js
Function incorporateWithdrawals(uint blockNr, bytes32 newState, bytes32 withdrawalRH)
``` 

Here, all withdrawal requests are processed, which were registered between the blocks blockNr and blockNr+19. `withdrawalRH` is the merkle root of all valid finalized withdrawals for the given block period.

Again, if the incorporatedWithdrawals results were incorrectly provided, this can be challenged. In case it is challenged, the solution submitter needs to provide the snark proof:

```
snark-withdrawals( 
		Public oldState
		Public: newState
		Public: exitRequestHash
		Private: [exitRequest informaiton]
		Private: [current balances] 
		Output: withdrawalRH
)
```	

This snark would check that:

- By hashing the `[exitRequest informaiton]`, we are getting the `exitRequestHash`
- Calculate the stateHash based on current balances and make sure it matches input
- for( withdrawal in `[exitRequest information]`) 
	- if `withdrawal.amount <= stateRHToken.amount`
		- Update the leaf with the current balance
		- incorporate the `withdrawal.amount` into `withdrawalRH`
- Recalculate the stateHash based on updated balances

After the challenge period has passed, any user can trigger their withdrawal by providing Merkle proof of the balance stored in `withdrawalAmounts[blockNr]`.

```js
Function processWithdrawal(uint blockNrOfReg, uint amount, address token, bytes MerkleProof){
	// Ensure sufficient time has passed
	require(blockNrOfReg + TimeDelta < now)

	// Verify that withdrawal is legit
	require(withdrawalAmounts[blockNrOfReg].CheckInclusionProof(amount, MerkleProof))

	// Update withdrawalAmounts[blockNrOfReg]

	// Transfer tokens
	require(Token(token).transfer(..))
}
``` 
	
## Feasibility-study

There are two main limiting factors for the scalability of this system. The costs associated with sending information to ethereum as payload and the number of constraints from the snarks.

### Order costs as payload


An order is constructed in the following manner: `(accountLeafIndex, fromTokenIndex, toTokenIndex, limitPrice, amount, signature)`. If impose the following constraints: 
- There are at most 2^6 different tokens in our exchange
- There are at most 2^16 different leafIndices
- Price is encoded with an accuracy of 64 bits using floating points (61 bits are exponent, last 3 are mantissa) 
- Amounts are encoded with an accuracy of 64 bits using floating points (61 bits are exponent, last 3 are mantissa)

Then we can store any order in 2 bytes32 and the total gas costs to k orders would be:

```
transaction initiation costs + k* order as payload costs + k* signature verification cost + k* hashing costs + updating the orderHashSha 
21000+k*(6+16+16+64+64)*68/8+k*3000+k*60+5000 
```

This means that up to 1000 orders can be stored within a single ethereum block .

### Constraints from snarks


The DIZK paper showed that it is possible to calculate snarks for up to several billion constraints. However, the parallelization described in this methods only works if the prime-1 of the underlying elliptic curve is sufficiently often divisible by 2. The prime-1 of the alt-bn128 curve from ethereum is divisible by 2^28 and hence, we can compute snarks for the constraints system with up to 2^28 ~ 268M constraints.



Certainly, our biggest constraint system comes with the snark checking the actual trade and updating all balances. In the following, we estimate the number of circuits by estimating how often we have to hash something. Such and estimation should suffice, as the total number of constraints is heavily dominated by the circuits of the hash function.

In the snark-applyAuction the snark circuits are dominated by the following operations:

- Check price matrix, trading welfare volume matches SHA256
	- #sha_constraints * ((bits_per_volume * orders) + (bits_per_float * tokens))
- Calculate sateHash (both old/new)
	- #pedersen_constraints * #accounts * #tokens * bits_per_float * 2
- Order hash validation
	- #pedersen_constraints * #order * #bits_per_order

We think that we can solve this problem e.g. for 100 tokens, 1k accounts and 10k orders per batch.

### Price manipulation	

One concern is that the limited space of orders is filled up by an attacker, after a profitiable market order (an order with a low limit sell price) was submitted. This way, the attacker could prevent fair price finding, as others wouldn't be able to submit their legitimate orders. Consequently, the attacker could profit from the off-price by buying the market order cheaply.

This can be prevent by two methods:

- **Order encryption:** Order can be encrypted using a distributed key generation sheme and only be decrypted after the order finalization is finished. Then the attacker would not be aware of the good price of an "market order".
- **Futures on order-participation:** A significant proportion (say 98%) of the order space would be distributed using the usual fee model while the rest (say 2%) could be reserved for people, who used their GNO/OWl or some other token. This way it would be much harder for an attacker to fill the order space.
