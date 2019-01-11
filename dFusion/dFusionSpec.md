# dFusion - decentralized scalable onchain exchange



A specification developed by Gnosis.


The following specification uses the snark application (snapp) onchain scaling approach, in order to build a scalable fully decentralized exchange with decentralized order matching. 
Scalability is achieved by storing only hashed information and allowing snarks to manipulate these through predefined logical gates [[link](https://ethresear.ch/t/on-chain-scaling-to-potentially-500-tx-sec-through-mass-tx-validation/3477)].
Orders are matched in a batch auction with an arbitrage-free price clearing technique developed by Gnosis: [Uniform Clearing Prices]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf).

## Summary
The envisioned exchange will enable `K` accounts to trade via limit orders between `T` predefined ERC20 tokens.
Limit orders are collected and matched in batches, with each batch containing up to `M` orders. 
Orders within a batch can be matched directly (e.g. an order trading token A for B against another order trading token B for A) or in arbitrarily long "ringtrades" (e.g. an order trading token A for B, with another one trading token B for C, with a third one trading token C for A).

The matching process is decentralized.
After orders have been collected over a certain amount of time, a batch is frozen and any sufficiently bonded participant can suggest a matching of orders in the current batch.

If more than one solution is submitted within a certain amount of time after the batch closes, the one that generates the largest "trader surplus" (detailed explanation below, for now think "trading volume") is selected and executed.
For this, the party that suggested the selected solution has to post enough information about the solution on-chain, so that any participant can quickly check the validity of the solution.

Anyone can challenge a solution on-chain (while providing a bond and an alternative solution) within a certain time-period after posting.
Such disputes are resolved by verifying a zkSnark proof on-chain that checks if the provided solution fulfills a number of constraints (specified in detail below).
If the verification succeeds, the challenger loses their bond and the state is "finalized". 
If the verification fails the original proposer loses their bond and the provided alternative state is assumed correct unless also challenged within a certain time.
In case no-one submits a proof, the verification automatically fails after a certain amount of time.

The reason for having such a bonded challenge-response interaction is that generating zkSnark proofs is very time consuming (much longer than the turnaround time we envision for each batch).
We therefore "optimistically" accept solutions and set a crypto-economic incentive to only post valid solutions.

## State stored in the smart contract

For each account, we chain each of ERC20 token balance together and store them as pedersen hash (not merkleized) in the anchor smart contract.
This "compressed" representation of all account balances is collision resistant and can thus be used to uniquely commit to the complete "uncompressed" state that lists all balances explicitly. 
The "uncompressed" state will be stored off-chain. All changes to the state will be announced via smart contract events. 
Thus, the full state will be fully reproducible for any participant by replaying all blocks since the creation of the smart contract. 
The following diagram shows how the "compressed" state hash is constructed:

![State construction](./dFusion%20rootHash.png?raw=true "State construction")

To allow `K` to be small, a bi-map of an accounts public key (on-chain address) to its `accountIndex` will be stored in the anchor contract as well. 
Accounts will pay "rent" to occupy an active account. The account index can be used to locate a users token balances in the state.

Furthermore, we store a bi-map of token address to its index `0 <= t <= T`, for each token that can be traded on the exchange.
When specifying tokens inside orders, deposits and withdrawel requests, we use the token's index `0 <= t <= T` instead of the full address.

As limit orders and deposits and withdrawal requests are collected they are not directly stored in the smart contract.
Doing so would require a `SSTORE` evm instruction for each item.
This would be too gas-expensive:
Assuming an order can be encoded in 256 bits, storing a batch of 10.000 on chain would cost ~5M gas (5.000 gas for SSTORE * 10.000 orders).
Instead the smart contract emits a smart contract event containing the relevant order information (account, from_token, to_token, limit) and stores a rolling SHA hash.
For a new order, the rolling hash is computed by hashing the previous rolling hash with the current order.

Any participants can apply pending deposit and withdrawl requests to the current account balance state.
To do so, they provide a new state commitment that represents all account balances after the application of pending requests.
Moreover, as the new state is stored on the smart contract, pending requests are reset.

When a party applies withdrawl requests to the account balance state, they also provide the list of valid withdraws (in form of their merkle root) which we store in the smart contract inside a mapping (`transitionId` -> `valid withdraw merkle root`).
Participants can later claim their withdraw by providing a merkle inclusion proof of their withdraw in any of the "valid withdraw merkle-roots".
This will transfer their tokens from the smart contract's into their public address.
In order to avoid double withdraws, we also store a bitmap for each "withdraw merkle-root".
Each bit in that maps denotes if the withdraw has alreay been claimed.

Participants can provide state transitions that apply pending deposits and withdrawls only while the order collection process is ongoing (the current batch is not yet frozen).
Since price finding and order matching is a computationally expensive task, we don't want the account state to change while the optimization problem is ongoing, as this could potentially invalidate correct solutions (e.g. a withdraw could lead to insufficient balance for a matched trade).
As soon as the matching of a closed batch is applied, pending withdrawls and deposits can again be applied to the state.

*// TODO state for snark challenge/response, e.g. hashBatchInfo*

To summarize, here is a list of state that is stored inside the smart contract:
- Hash of all token balances for each account chained together (Pedersen)
- Bi-Map of accounts public keys (ethereum addresses) to dƒusion accountId
- Bi-Map of ERC20 token addresses to internal dƒusion tokenId that the exchange supports
- Rolling hash of pending orders, withdrawls and deposit requests (SHA)
- Map of stateTransitionId to pair of "valid withdrawel requests merkle-root" (SHA) and bitmap of already claimed withdraws
- Current state of the batch auction (e.g. *price-findeing* vs. *order-collection*)

## Batch Auction Workflow

The trading workflow consists of the following sequential processes:
1. On-Chain order collection
2. Finding the batch price: 
tion of batch trading surplus (off-chain)
3. Verifying batch price and trade execution (zkSnark)
4. Restart with step 1

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
			byte32 oldHashSha = orderHashSha
			orderHashSha = Kecca256(oldHashSha, orders[i]) 
			emit OrderSubmitted(oldHashSha, orders[i], orderHashSha)
		}
	}
}
```

This function will update the rolling hash of pending orders, chaining all orders with a valid signature. 
This function is callable by any party. 
However, it is possible that “decentralized operators” accept orders from users, bundle them and then submit them all together in one function call. 

Notice, that the orders are only sent over as transaction payload, but will not be “stored” in the EVM (to save gas).
All relevant information is emitted as events.
This will allow any participant to reproduce all orders of the current batch by replaying the ethereum blocks since batch creation and filtering them for these events.

Also notice, that we allow orders, which might not be covered by any balance of the order sender. 
These orders will be sorted out later in the settlement of an auction.

### Finding the batch price: optimization of batch trading surplus (off-chain)

After a certain time-frame or once the maximum number of orders per batch are collected, a batch is "frozen" and the orders participating in it are final.
A new batch could immediately start collecting new orders while the previous one is being processed.
To process a batch, participants compute the uniform clearing price maximizing the trading surplus between all trading pairs can. 
The traders surplus of an order is defined as the difference between the uniform clearning price and the limit price, multipied by the volume of the order with respect to some reference token. 
The exact procedure is described [here]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf). 
Calculating the uniform clearing prices is an np hard optimization problem and most likely the global optimum will not be found in the pre-defined short time frame: `SolvingTime` - we think that 3-10 minutes are reasonable. 
While it is a pity that the global optimum cannot be found, the procedure is still fair, as everyone can submit their best solution.
Since posting the complete solution (all prices and traded volumes) would be too gas expensive to put on-chain for each candidate solution, participants only submit the 'traders surplus' they claim there solution is able to achieve.
The anchor contract will store all submissions and will select the solution with the maximal 'traders surplus' as the final solution.

This means the uniform clearing price of the auction is calculated in a permission-less decentralized way.	
Each time a solution is submitted to the anchor contract, the submitter also needs to bond themselves so that they can be penalized if their solutions later turns out incorrect.
The participant providing the winning solution will later also have to provide the updated account balances that result from applying their order matching.
In return for their efforts, solution providers will be rewarded with a fraction of transaction fees that are collected for each order.

### Verifying batch price and trade execution (zkSnark)

After the solution submission period, the best solution with the highest trading surplus will be chosen by the anchor contract. 
The submitter of this solution then needs to post the full solution into the ethereum chain as calldata payload. 
The solution is a new stateHash with the updated account balances, a price vector `P`:

| P | Token_1:Token_1 | ... | Token_T:Token_1|
| --- | --- | --- | --- | 
| price | p_1 | ... | p_T |


of all prices relative to a reference token `Token_1`. Since prices are arbitrage-free, we can calculate the `price Token_i: Token_k` =  `(Token_i:Token_1):(Token_1:Token_k)`.

Along with the prices, the solution submitter also has to post a vector `V` of `buyVolumes` for each order:

| V | order_1 | ... | order_K|
| --- | --- | --- | --- |
| buyVolume | o_1 | --- | o_K |

Anyone can caluclate the `sellVolume` from the price of the token pair and the buyVolume.

The solution submitter also submits a pedersen hash of all orders that were inside the applied batch.
This pedersen hash is assumed to be equivalent to the sha hash of all orders that is already stored in the smart contract (the equivalence can be challenged).
The reason we prefer having the hash as a pedersen hash is that it can be calculated much more efficiently inside a snark.
The size of our batch is bound by the amount of orders that the `applyAuction` snark (see below) can compute.
By spending less computation on hashing we can fit process larger batches inside `applyAuction`.

*//TODO what if the participant that claimed the surplus never submits? Are we sequentially degrading to second best, third best solution, or at that point allowing any solution?*

The new state is optimistically assumed correct and the pedersen hash equivalent of orderHash is stored alongside as trasition metadata. 
V and P are provided as data payload to the anchor contract which will hash them together into `hashBatchInfo` (which is also stored as transition metadata).
With this hash the solution is unambiguously "committed" on-chain with a minimum amount of gas.
If someone challenges the solution later, the smart contract can verify that a proof is for this particular solution by requiring that the private inputs to the proof hash to the values stored metadata.

The full uncompressed solution is also emitted as a smart contract event so that everyone can check whether the provided solution is actually a valid one. 
If it is not valid, then anyone can challenge the solution submitter (again providing a bond and an alternative solution).

*// TODO: I could "win" the price-finding by committing to an absurdly large surplus, then submit a wrong solution, challenge myself with a correct solution that is much worse than the second surplus best.*

There are two types of challenges:
1.) Challenging that the pedersen hash of all orders doesn't match the sha hash already stored in the smart contract
2.) Challenging that the matching logic is incorrect (e.g. not arbitrage free, not respecting limit prices of an orders, or adjusting balance incorrectly)

To resolve a challenge of type 1), the solution submitter needs to prove that his solution is correct by providing proof for the following zkSnark:

```
zkSnark - TransitionHashes&Validation ( public input: orderHashSha,
					public input: orderHashPedersen,
					Private input: [orders])
```

It will do the following checks:

- `orders` hashes to `input.orderHashSha`
- `orders` hashes to `input.orderHashPedersen`

To resolve a challenge of type 2), the solution submitter needs to prove that his solution is correct by providing proof for the following zkSnark:

```
zkSnark - applyAuction(
	Public: state,
	Public: tradingSurplus,
	Public: hashBatchInfo,
	Public: orderHash,
	Private: priceVector,
	Private: volumeVector,
	Private: balances,
	Private: orders,
	Output: newstate
)
```
The snark verifies the following:

- `priceVector` and `buyVolumes` hashes to `input.hashBatchInfo` (with sha)
- `balances` hashes to `input.state` (with pedersen)
- `orders` hashes to `input.orderHash` (with pedersen)

- for each `order` in `orders`
	- `order.buyVolume` and `order.sellVolume` have same ratio as `order.buyToken` and `order.sellToken`
	- Verify tnhe order only has non-zero volume if the limit price is below the market price
	- Verify the order has not more volume than specified in `order.amount`
	- Calculate trader surplus for this order
	- Increment total surplus according to surplus of order
	- Increment `totalSellVolume[order.sellToken]` by `order.sellAmount`
	- Increment `totalBuyVolume[order.BuyToken]` by `order.buyAmount`
	- Update the balance of the order author by subtracting `order.sellVolume` from `balance[order.sellToken]`
	- Update the balance of the order author by addint `order.buyVolume` from `balance[order.buyToken]`
	
- For all tokens `t`, check that `totalSellVolume[t] == totalBuyVolume[t]` (solution doesn't mint or burn tokens)
- Check that `tradingSurplus == input.tradingSurplus`
- For all balances, check that `balance > 0` 
- return `newstate` by hashing all balances together (with pedersen)

## Processing of pending exits and deposits (zkSnark)

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
