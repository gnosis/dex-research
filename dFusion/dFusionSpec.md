# dFusion - decentralized scalable onchain exchange



Specification develop by Gnosis.


The following specification uses the scaling approach from Vitaliks post: [Onchain scaling](https://ethresear.ch/t/on-chain-scaling-to-potentially-500-tx-sec-through-mass-tx-validation/3477) in order to build a scalable fully decentralized exchange with decentralized order matching. The scalability is enabled by the heavy use of zk-snarks. In order to allow bigger circuit amounts, we are planning to use the ideas descibed in [DIZK](https://www.usenix.org/system/files/conference/usenixsecurity18/sec18-wu.pdf). Orders are matched in a batch auction with a arbitratrage-free price clearing technique developed by Gnosis: [uniform clearning prices]( https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf)


## Specification
The specification will allow to trade via limit orders between N ERC20 tokens.
For each ERC20 token we store the balance of traders in a Merkle tree root hash:
	 `balanceTreeRootHash_I    for 0<I<=N`

Each leaf contains only the amount of tokens held by a user.
The addresses of the accounts in the exchange are stored in another Merkle tree
Root hash:
	`accountsRootHash`

The balance of the i-th leaf from the `balanceTreeRootHashToken` will belong to the account of the i-th leaf in `accountsRootHash`.

All orders are encoded as limit sell orders: `(accountLeafIndex, fromTokenIndex, toTokenIndex, limitprice, amount, signature)`. The order should be read in the folllowing way: the user from the specified leaf index would like to sell the token fromTokenIndex for toTokenIndex for at most the limit price and the amount specified.
All these roothashes `[ accountsRootHash, balanceTreeRootHash_1, …, balanceTreeRootHash_1]` are getting hashed together and will be stored in a `balancesRootHash` in the a “anchor” smart contract on-chain.

The trading workflow consists of the following sequential processes:
1. Order collection (with Sha hashes)
2. Transition function from Sha to Pederson & order validation
3. Finding batch price: optimization of batch trading volume
4. Balance updates after trade execution via 
5. Processing of pending exit, depositssnark

### Order collection(with Sha hashes)

The anchor smart contract on ethereum will offer the following function:
```
function appendOrders( bytes32 [] orders){ 
// some preliminary checks, which will limit the total amount of orders..

// update of orderHashSha
	for(i=0;i<orders.length;i++){
	orderHashSha = Kecca256( orderHashSha, order[i])
}
}
```
, which simply updates an orderHashSha variable, which is encoding all orders. This function is callable by any party. But it is expected that “decentralized operators” accept orders of users, bundle them and then include them all together into the function. Notice that the orders are only send over as transaction payload, but will not “stored” in the EVM.

### Transition function from Sha to Pederson & order validation

In the first step the orders are hashed together using sha. This makes sense as sha is very cheap on the evm. However, sha is very “expensive” in snarks and hence we are forced to recalculate the hashes in pederson hashes. 

We will use a snark to do this job:
```
Snark - TransitionHashes&Validation ( public input: orderHashSha,
					Private input: [orders])
					Output: orderHashPederson
```
The transitionHashes&Validation snark will do the following checks:
- Verify the private input by sha-hashing the orders together into calculatedHash and check that `calculatedHash = = orderHashSha` 
- Iterate over all order and sort out the orders, where the signature does not match address specified in the accountLeafIndex
- Iterate over all remaining orders and hash them together via a merkle tree into the public output using the pederson hash.

Notice that we allow orders, which might not be covered by any balance of the order sender.

In the anchor contract, we have the following functionality for this process:

Anyone can propose a transition to the anchor contract by providing the required information and by providing a very high bond. It is not required to provide the snark in the first place:
```
Function submitTransitionInformation( bytes32 oldstate, bytes32 newstate)
```
In case the send transition information are incorrect, anyone can challenge it by also providing a huge bond and calling the following function.
```
Function challengeTransitionInformation( bytes32 oldstate, bytes32 newstate)
```
If the first transition submitter can provide a snark within a predefined time frame (some hours) proving that his transition was correct, the challenge will not be successful. Otherwise it will be successful. The snark would be evaluated by the anchor contract after calling the following function.
Function submitSnarkToResolveChallenge(bytes32 oldstate, bytes32 newstate, --snark--)


### Finding batch price: optimization of batch trading volume

After the previous step, the orders participating in a batch have finalized. Now, the uniform clearing price maximizing the trading volume between all trading pairs can be calculated. Calculating the uniform clearing prices is an np hard optimization problem and most likely the global optimum will not be found in the pre-defined short time frame: 3 minutes. While it is a pity that the global optimum can not be found, the procedure is still fair, as everyone can submit their best solution. The anchor contract will store all submissions and maximal trading volumes and will select the solution with the maximal trading volume.
This means the uniform clearing price of the auction is calculated in a permission-less decentralized way.	
Each time a solution is submitted to the anchor contract, of course, the submitter also needs to bond himself. If he provides the solution, he also has to provide in the next process step the balance update information and answer any challenge request.




The details of the price finding mechanism can be found in the following paper:
https://github.com/gnosis/dex-research/blob/master/BatchAuctionOptimization/batchauctions.pdf


### Balance updates after trade execution via snark


After the price submission period, the best solution with the highest trading volume will be chosen by the anchor contract. The submitter of this solution needs to do 2 steps:

1) posting the full solution into the ethereum chain as payload. The solution is a price vector P, a new balanceRootHash with the updated account balances and a trading volume matrix S:

| P | Token_1:Token_1 | ... | Token_N:Token_1|
| --- | --- | --- | --- | 
| price | p_1 | ... | p_N |


P is only the price vector of all prices relative to a reference token Token_1. As prices are arbitrage-free, we can calculate the price Token_i: Token_k =  (Token_i:Token_1):(Token_1:Token_k)





| S | Token_1 | Token_2 | ... | Token_N|
| --- | --- | --- | --- | --- | 
| Token_1 | x | (p_12, f_12) | ... | (p_1N, f_1N) |
| Token_2 | (p_21, f_21) | x | ... | (p_2N, f_2N) |
| ... | ... | ... | ... | ... |
| Token_2 | (p_N1, f_N1) | (p_N2, f_N2) | .. | x |


In this matrx S, the price is the price of the fractionally fulfilled orders and the fraction is, of course, the fraction of its partial fulfillment. The information of the matrix S are needed in order to determine exactly  the unique solution. We will not explain it here in detail, we refer to the paper cited above.

These two parts of the solution S and P must be provided as data payload to the anchor contract and then the anchor contract will hash them together into hashBatchInfo.


Now, everyone can check whether the provided solution is actually a valid one. If it is not a valid, then anyone can challenge the solution submitter. If this happens, the solution submitter needs to prove that his solution is correct by providing the following snark:
```
Snark - applyAuction(
	Public: balanceRootHash,
	Public: trading volume,
	Public: hashBatchInfo,
	Public: orderHashPederson,
	Private: priceMatrix PxP
	Private: tradingInfoMatrix S
	Private: [ balanceTreeRootHash_I    for 0<I<=N]
	Private: orders
	Private: touched balances + leaf number + balance merkle proofs per order,
	Private: FollowUpOrderOfAccount [index of later order touching balance])
	Output: newBalanceRootHash
```
The snark would check the following things:

- priceMatrix has actually the values as induced by the hashBatchInfo
- tradingInfoMatrix S has actually the values induced by the hashBatchInfo
- verify  [ balanceTreeRootHash_I    for 0<I<=N] with balanceRootHash

- for order in [orders]
	- open balance leaf of the receiving account 
	- check that the leaf is owned by sender by opening the accountIndexLeaf
	- add trading volume to balance, if order is executed
	- if FollowUpOrderOfAccount == 0
		- check that balance is positive
	- else 
		Check that the other order referenced in FollowUpOrderOfAccount has the same sender or receiver and it touches the balance

	- close balance leaf
		
	- open balance leaf of the sending account 
	-check that the leaf is owned by sender
	- subtract trading volume to balance, if order is executed
	- if FollowUpOrderOfAccount
		- check that balance is positive
	- else 
		Check that the other order referenced in FollowUpOrderOfAccount has the same sender or receiver and it touches the balance

	- recalculate the balanceRoothash with new balance leaf

	- Update the balanceRootHash
	- Keep track of total trading volume
- End
- For all token, check that sell volume equals buy volume
- Check that the calculated total trading volume equals the public input.
- Check the order fairness criteria



### Processing of pending exit, deposits

Deposits and withdraws need to be processed and incorporated into the balance hashes as well. For this we make again use of snarks and specific challenging periods.

If someone want to deposit to anchor contract, we would have to send funds into the follwoing function of the anchor contract:

```
Function deposit ( address token, uint amount){
// verify that not too much deposits have already been done,


	// sending of funds
	require( Token(token).transferFrom())

	// 
	depositHash[blocknr/20] = sha256(depositHash[blocknr/20], msg.sender, amount, token) 
}
```

That means that all the depositing information are stored in a bytes32 depositHash. Each 20 ethereum blocks, we store all the occuring depositsHash in a unique hash.

The deposits can be incorporated by any highly bonded party by calling the following function:
```
Function incorporateDeposits(uint startingBlockNr, unit endingBlockNr, oldBalanceHash, newBalanceHash)
```
This function would update the the balanceHash by incorporating the deposits from startingBlockNr to endingBlockNr.

Everyone can check whether the balanceHash has been updated correctly. If it has not been updated correctly, then the person submitting this solution can be challenge by providing a bond.

If the submitter is challenged, he would have to provide the following snark:

```
snark-deposits( Public oldBalanceHash
		Public newBalanceHash
		Public depositHash
		Private: [deposit informations]
		Priavte: [current balances, merkleProof] )
```	

This snark would check that:

```	
		By hashing the [deposit information], we are getting the depositHash
		for( deposits in [deposit information]){
			Opening the Leaf of with the current balance,
			Opening the Leaf of the AccountHash and 
			check that deposit.sender == accountLeaf.address
			Update the leaf with the current balance,
			Recalculate the balanceHash
		}
```		

Something quite similar will be done with exit request. There is only one think we have to take care of: 
	Exits should only occur after some time delay, as otherwise an illegal state transition might not yet have been challenged.
	
Feasibility-study


Biggest forseen challenge: Generating a trusted setup with 2^28 constraints.

