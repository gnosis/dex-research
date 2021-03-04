

### Optimization Examples for certain problem

The following scripts calculate certain metrics for proposed solutions of a certain optimization problem.

#requirements:
```
pip install jsonmerge
```

#test case:
Run the following function call
```
apply_solution("problem_testcase.json",solution_testcase.json)
```
Testcase is currently not working, as rounding is not correct. With:
```
	def getSellAmount(buyAmount, buyToken, sellToken, fee = feeConstant):
		return buyAmount * prices[buyToken] / prices[sellToken] // (1- fee)
```
it works.


#Execution
```
python2 dfusion.py
```
