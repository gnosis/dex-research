import json
from collections import defaultdict
from jsonmerge import Merger

schema = {
            "properties": {
                 "*": {
                     "mergeStrategy": "append"
                 }
             }
         }

merger = Merger(schema)



def apply_solution(problem_file, solution_file):

	feeConstant = 0.001

	# sell ... for ...
	def getPrice(token1, token2, fee = feeConstant):
		return prices[token1] / prices[token2] * (1 - fee)

	def getSellAmount(buyAmount, buyToken, sellToken, fee = feeConstant):
		return buyAmount * prices[buyToken] / prices[sellToken] / (1- fee)

	with open(problem_file, 'r') as f:
		problem = json.load(f)

	with open(solution_file, 'r') as f:
		solution = json.load(f)
    
	
	solution = merger.merge(problem, solution) 

	prices = solution["prices"]
	orders = solution["orders"]

	print getPrice("S1", "S2")

	delta = defaultdict(int)
	counter = 0
	utility = 0
	utility_with_negatives = 0
	utility_from_solution = 0
	for i in orders:
		j = orders[i]
		if "execBuyAmount" not in j:
			j["execBuyAmount"] = 0

		j["execSellAmount"] = getSellAmount(j["execBuyAmount"], j["buyToken"], j["sellToken"])

		if j["execBuyAmount"] > 0:
			#limit price needs to be below clearing price
			assert not j["execBuyAmount"] / j["execSellAmount"] < j["limitRate"][1][0] / j["limitRate"][0][0], j
		delta[j["buyToken"]] -= j["execBuyAmount"]
		delta[j["sellToken"]] += j["execSellAmount"]

		#(how much token did they got - how much token did they expect) * converted to fee token price
	
		utility_in_buy_token = j["execBuyAmount"] - j["execSellAmount"] * j["limitRate"][1][0] / j["limitRate"][0][0]
		utility += utility_in_buy_token * getPrice(j["buyToken"], "FEE", 0)
		utility_with_negatives += utility_in_buy_token * getPrice(j["buyToken"], "FEE", 0)
		if j["sellToken"] == 'S1':
			utility_for_special_token = utility_in_buy_token * getPrice(j["buyToken"], j["buyToken"], 0)
		if "execUtility" in j.keys():
			utility_from_solution += j["execUtility"]

		#the difference between the max utility they could have gotten, vs what they actually have gotten.
		# how much token they would have gotten 
		if getPrice(j["sellToken"], j["buyToken"]) > j["limitRate"][1][0] / j["limitRate"][0][0]:
			max_utility = j["maxSellAmount"] * getPrice(j["sellToken"], j["buyToken"]) - j["maxSellAmount"] * j["limitRate"][1][0] / j["limitRate"][0][0]
			max_utility_in_fee_token = max_utility * getPrice(j["buyToken"], "FEE", 0)
			disregarded_utility = max_utility_in_fee_token - utility_in_buy_token * getPrice(j["buyToken"], "FEE", 0)
			utility_with_negatives -= disregarded_utility

			#print i
			#print disregarded_utility


	for token in delta:
		if token != "FEE":
			assert abs(delta[token]) < 0.02, delta


		counter += 1
	#print delta
	print "Total utility: " + str(utility)
	print "Total utility with disregarded util: " + str(utility_with_negatives)
	print "Total utility for only S1 token: " + str(utility_for_special_token)
	print ""

	
filenames = ['solution_expected_best_one.json', 'solution_best_disregarded_utility.json', 'solution_expected_best_one_with_FT_to_null.json']

for i in filenames:
	print i
	apply_solution("problem.json",i)