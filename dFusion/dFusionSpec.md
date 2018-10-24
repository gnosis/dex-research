# dFusion - decentralized scalable onchain exchange



A specification developed by Gnosis.


The following specification uses the snark application (snapp) onchain scaling approach, in order to build a scalable fully decentralized exchange with decentralized order matching. The scalability is enabled storing information only in merkle root hashes and allow snarks the manipulation of these root hashes in predefined logic gates [cp](https://ethresear.ch/t/on-chain-scaling-to-potentially-500-tx-sec-through-mass-tx-validation/3477). In order to allow bigger number of constraints for the snarks, we are planning to use the ideas described in [DIZK](https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-wu.pdf). Orders are matched in a batch auction with an arbitrage-free price clearing technique developed by Gnosis: [Uniform Clearing Prices]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf).

## Specification
The envisioned exchange will enable users to trade via limit orders between N predefined ERC20 tokens.
For each ERC20 token we store the balance of traders in a Merkle tree root hash:
`balanceTRH_I    for 0<I<=N`. In this tree, each leaf contains only the amount of tokens held by a user.

The addresses and nounces of the accounts in the exchange are stored in another Merkle tree
root hash:
	`accountsRH`

The balance of the i-th leaf from the `balanceTRH_Token` will belong to the account of the i-th leaf in `accountsRH`.

All orders are encoded as limit sell orders: `(accountLeafIndex, fromTokenIndex, toTokenIndex, limitPrice, amount, nounce, signature)`. The order should be read in the following way: the user from the specified leaf index would like to sell the token fromTokenIndex for toTokenIndex for at most the limit price and the amount specified.


All these root hashes `[accountsRH, balanceRH_1, ..., balanceRH_N]` are getting hashed together and will be stored in a `stateTRH` in the “anchor” smart contract on-chain. The anchor contract will store all relevant information for this snapp exchange.

![Variable Build up](./variables.png?raw=true "Variables")


The trading workflow consists of the following sequential processes:
1. Order collection (with sha hashes)
2. Transition function from sha to Pederson hashes 
3. Finding the batch price: optimization of batch trading surplus
4. Balance updates after trade execution 
5. Processing of pending exits and deposits
6. Restart with step 1

### Order collection (with sha hashes)

The anchor smart contract on ethereum will offer the following function:
```
function appendOrders( bytes32 [] orders){ 
	// some preliminary checks, which will limit the total amount of orders..

	// update of orderHashSha
	for(i=0;i<orders.length;i++){
		if( "check signature of order"){
			// hash order without signature
			orderHashSha = Kecca256( orderHashSha, order[i]) 
		}
	}
}
```
This function will simply update an orderHashSha variable, which is encoding all orders with a valid signature. This function is callable by any party. However, it is expected that “decentralized operators” accept orders from users, bundle them and then include them all together into the function. Notice that the orders are only sent over as transaction payload, but will not be “stored” in the EVM.

### Transition function from sha to Pederson hashes 

In the first step, the orders are hashed together using sha. This makes sense as sha is very cheap on the evm. However, sha is very “expensive” in snarks and hence we are forced to recalculate the hashes in Pederson hashes. 

We will use a snark to do this job:
```
Snark - TransitionHashes&Validation ( public input: orderHashSha,
					Private input: [orders])
					Output: orderHashPederson
```
The transitionHashes&Validation snark will do the following checks:
- Verify the private input by recalculating the sha of all orders and comparing it to the public input `orderHashSha`.
- Iterate over all orders again and hash them sequencially using the Pederson hash. Use this hash as output.

Notice that we allow orders, which might not be covered by any balance of the order sender.

In the anchor contract, we have the following functionality for this process:

Anyone can propose a transition to the anchor contract by providing the required information and by providing a very significant bond. It is not required to provide the snark in the first place:
```
Function submitTransitionInformation( bytes32 oldstate, bytes32 newstate)
```
In case the send-transition information is incorrect, anyone can challenge it by also providing a significant bond and calling the following function.
```
Function challengeTransitionInformation( bytes32 oldstate, bytes32 newstate)
```
If the first transition submitter can provide a snark within a predefined time frame (some hours) proving that his transition was correct, the challenge will not be successful. Otherwise, it will be successful.

The snark would be evaluated by the anchor contract after calling the following function.
 ```
Function submitSnarkToResolveChallenge(bytes32 oldstate, bytes32 newstate, --snark--)
```

### Finding batch price: optimization of batch trading surplus

After the previous step, the orders participating in a batch have finalized. Now, the uniform clearing price maximizing the trading surplus between all trading pairs can be calculated. The traders surplus of one order is the difference between the uniform clearning price and the limit price, multipied by the volume of the order with respect to some reference token. The exact procedure is described [here]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf). Calculating the uniform clearing prices is an np hard optimization problem and most likely the global optimum will not be found in the pre-defined short time frame: `SolvingTime` - we think that 3-10 minutes are reasonable. While it is a pity that the global optimum cannot be found, the procedure is still fair, as everyone can submit their best solution. The anchor contract will store all submissions and will select the solution with the maximal 'traders surplus' as the final solution. We define the traders surplus as the sum of all differences between the uniform clearning prices and the limit price of an touched order multiplied by the surplus of the order.

This means the uniform clearing price of the auction is calculated in a permission-less decentralized way.	
Each time a solution is submitted to the anchor contract, of course, the submitter also needs to bond himself. If he provides the solution, he also has to provide in the next process step the balance update information and has to answer any challenge request.


### Balance updates after trade execution


After the price submission period, the best solution with the highest trading surplus will be chosen by the anchor contract. The submitter of this solution needs to do 2 steps:

1) posting the full solution into the ethereum chain as payload. The solution is a price vector P, a new balanceRootHash with the updated account balances, a vector of trading surpluss (VV) for each order.

| P | Token_1:Token_1 | ... | Token_N:Token_1|
| --- | --- | --- | --- | 
| price | p_1 | ... | p_N |


`P` is only the price vector of all prices relative to a reference token `Token_1`. As prices are arbitrage-free, we can calculate the `price Token_i: Token_k` =  `(Token_i:Token_1):(Token_1:Token_k)`

Unfortunately, not all orders below the limit price will be filled completely. It might happen that the account sending the order might not have the balance required to settle the sell order. These orders we are calling uncovered orders and they need to be excluded or only partly be filled. Because of this, the solution submitter needs to provide for each order the fraction of the traded surplus:

| VV | order_1 | ... | order_K|
| --- | --- | --- | --- |
| fraction | o_1 | --- | o_K |



These two parts of the solution: VV and P must be provided as data payload to the anchor contract and then the anchor contract will sha-hash them together into `hashBatchInfo`.

Now, everyone can check whether the provided solution is actually a valid one. If it is not valid, then anyone can challenge the solution submitter. If this happens, the solution submitter needs to prove that his solution is correct by providing the following snark:
```
Snark - applyAuction(
	Public: stateRH,
	Public: tradingWelfare,
	Public: hashBatchInfo,
	Public: orderHashPederson,
	Private: priceMatrix PxP,
	Private: orderVolume
	Private: [ balanceTRH_I    for 0<I<=N]
	Private: orders
	Private: touched balances + leaf number + balance merkle proofs per order,
	Private: FollowUpOrderOfAccount [index of later order touching balance])
	Output: newstaetRH
```
The snark would check the following things:

- `priceMatrix` has actually the values as induced by the `hashBatchInfo` (with sha)
- `orderVolume` VV has actually the values induced by the `hashBatchInfo` (with sha)
- verify  `[ balanceTRH_I    for 0<I<=N]` hashes to `balanceRH`
- verify  `[VV]` has the values induced by `hashBatchInfo`

- for order in [orders]
	- open balance leaf of the receiving account by check balance + proof in `stateRH`
	- check that the leaf is owned by sender by opening the accountIndexLeaf
	- check that the nounce is valid and update it
	- read the potentially fractional surplus of the order
	- update the balance by substracting sell volume
	- if `FollowUpOrderOfAccount` == 0
		- check that balance is positive
	- else 
			Check that the other order referenced in `FollowUpOrderOfAccount` has the same receiver and it touches the balance
	- update the balance by adding buy volume
	- close balance leaves and update Merkle tree hashes
	- Keep track of the total `selling surplus` per token
	- Keep track of the total `buying surplus ` per token
	- Keep track of the total `selling volume` per token
	- Keep track of the total `buying volume ` per token
	
- For all token, check that `selling volume` equals `buying volume`
- Check that the calculated total trading surplus equals the public input `tradingWelfare`.


### Processing of pending exit, deposits

Deposits and withdraws need to be processed and incorporated into the 'balanceRH' as well. For this, we make again use of snarks and specific challenging periods.

If someone wants to deposit to anchor contract, we would have to send funds into the following function of the anchor contract:

```
Function deposit ( address token, uint amount){
	// verify that not too much deposits have already been done,

	// sending of funds
	require( Token(token).transferFrom(...))

	// Storing deposit information
	depositHash[blocknr/20] = sha256(depositHash[blocknr/20], msg.sender, amount, token) 
}
```

That means that all the depositing information are stored in a bytes32 `depositHash`. Each 20 ethereum blocks, we store all the occurring `depositsHash` in a unique hash.

The deposits can be incorporated by any significantly bonded party by calling the following function:
```
Function incorporateDeposits(uint blockNr, oldBalanceHash, newBalanceHash)
```
This function would update the `stateRH` by incorporating the deposits received from `blockNr` to `blockNr+19`.

Everyone can check whether the `stateRH` has been updated correctly. If it has not been updated correctly, then the person submitting this solution can be challenge by providing a bond.

If the submitter is challenged, he would have to provide the following snark:

```
snark-deposits( Public oldBalanceHash
		Public newBalanceHash
		Public depositHash
		Private: [deposit informations]
		Priavte: [current balances, merkleProof] )
```	

This snark would check that:

- By hashing the `[deposit information]`, we are getting the `depositHash`
- for( deposits in `[deposit information]`)
	- Opening the Leaf of with the current balance,
	- Opening the Leaf of the AccountHash and 
	- check that `deposit.sender == accountLeaf.address`
	- Update the leaf with the current balance,
	- Recalculate the stateRH
		

Something quite similar will be done with exit requests. There is only one thing we have to take care of: 
Exits should only occur after some time delay, as otherwise an illegal state transition might not yet have been challenged.

If a users want to exit, he first needs to do an exit request by calling the following function in the anchor contract:
```
Function exitRequest ( address token, uint amount){
	// verify that not too much exists request have already been done,

	// sending of funds
	require( Token(token).transferFrom(...))

	// Storing deposit information
	exitRequestHash[blocknr/20] = sha256(exitRequestHash[blocknr/20], msg.sender, amount, token) 
}
```

Then any significantly bonded party can incorporate these bundled exit requests into the current stateRH by calling the following function:

```
Function incorporateWithdrawals(uint blockNr, bytes32 oldBalanceHash, bytes32 newBalanceHash,bytes32 withdrawalAmounts)
``` 
Here, all withdrawal request was processed, which were registered between the blocks blockNr and blockNr+19. A solution submitter would have to hand over the previous oldBalanceHash, which describes the balances before the withdrawals. It would have to send over the newBalanceHash describing the new balances of the users and withdrawalAmounts, which is also the balancesHashed together from all legit withdrawals from all users.

Again, if the incorporatedWithdrawals results were incorrectly provided, this can be challenged. In case it is challenged, the solution submitter needs to provide the snark proof:

```
snark-withdrawals( Public oldBalanceHash
		Public newBalanceHash
		Public exitRequestHash
		Private: [exitRequest informaiton]
		Priavte: [current balances, merkleProofs] )
		Output: withdrawalAmounts
```	

This snark would check that:

- By hashing the `[exitRequest informaiton]`, we are getting the `exitRequestHash`
- for( withdrawals in `[exitRequest information]`)
	- Opening the leaf of with the current balance,
	- Opening the leaf of the accountHash and 
	- if `withdrawal.sender == accountLeaf.address` && `withdrawal.amount <= stateRHToken.amount`
		- Update the leaf with the current balance,
		- Recalculate the stateRH
		- incorporate the `withdrawal.amount` into `withdrawalAmounts`


If a provided solution is not challenged, any users can trigger his withdrawal 1 day after the submission, by providing Merkle proof of his balance stored in withdrawalAmounts[blockNr]

```
Function processWithdrawal(uint blockNrOfReg, uint amount, address token, bytes MerkleProof){
	// check that some time passed
	require(blockNrOfReg + TimeDelta < now)

	// Verify that withdrawal is legit
	require(withdrawalAmounts[blockNrOfReg].CheckInclusionProof(amount, MerkleProof))

	//Update withdrawalAmounts[blockNrOfReg]

	//Transfer tokens
	require(Token(token).transfer(..))
}
``` 
	
	
## Feasibility-study

There are two main limiting factors for the scalability of this system. The costs associated with sending information to ethereum as payload and the number of constraints from the snarks.

### Order costs as payload

An order is constructed in the following manner: `(accountLeafIndex, fromTokenIndex, toTokenIndex, limitprice, amount, signature)`. If we put on the following constraints: 
- We do have only 2^6 different tokens in our exchange
- We do have only 2^16 different leafIndices
- price is encoded with an accuracy of 64 bits using floating points (61 bits are exponent, last 3 are mantissa) 
- amounts are encoded with an accuracy of 64 bits using floating points (61 bits are exponent, last 3 are mantissa)
- signature is a pair (s, r, v), where s and r are numbers potentially as big as the elliptic curve prime number. That means (r, s) -> 512 bits
Then we can store any order in 3 bytes32 and the total gas costs to k orders would be:
```
transaction initiation costs + k* order as payload costs + k* signature verification cost + k* hashing costs + updating the orderHashSha 
21000+k*(6+16+16+64+64+512)*68/8+k*3000+k*60+5000 
```
This means that with 7.4 million gas one can easily store 1000 orders.

### Constraints from snarks


The DZIK paper showed that it is possible to calculate snarks for up to several billion constraints. However, the parallelization described in this methods only works if the prime-1 of the underlying elliptic curve is sufficiently often divisible by 2. The prime-1 of the alt-bn128 curve from ethereum is divisible by 2^28 and hence, we can compute snarks for the constraints system with up to 2^28 ~ 2.6B constraints.


Certainly, our biggest constraint system comes with the snark checking the actual trade and updating all balances. In the following, we estimate the number of circuits by estimating how often we have to hash something. Such and estimation should suffice, as the total number of constraints is heavily dominated by the circuits of the hash function.

In the snark-applyAuction the snark circuits are dominated by the following operations:

- iteration over all orders -> constraints multiply #orders
- for each order we open 3 leaves: accountLeaf, balanceLeaf_SendingToken, balanceLeaf_ReceivingToken -> 3 * log_2(#balances) * 2 * #pedersonHashConstraints
- for each order we recalculate the merkle root: accountLeaf, balanceLeaf_SendingToken, balanceLeaf_ReceivingToken -> log_2(#balances) * 2 * #pedersonHashConstraints

That means that the number of constraints for #orders will be about #orders * log_2(#balances) * 8 * #pedersonHashConstraints implying that we could process roughly 5K orders with 1M accounts, if there are  2K constraints per pedersonHash.



Biggest foreseen challenge: Generating a trusted setup with 2^28 constraints.