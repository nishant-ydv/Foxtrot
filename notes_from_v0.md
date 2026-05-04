1. can we select multiple categories
2. can we select multiple departments in those categories
3. Budget ($) change to Budget($M) to avoid showing so many zeroes or $K if lower numbers put in
4. for service target give both slider and box, the box should invalidate if expecte numbers are not enetered
5. show total cost and budget remaining in $M example $12.1M cost $5M budget remaining, can there be a way to quantify risk here, markdown risk or sales loss risk
6. what exactly is this reorder point, i do not understand numbers, are these untis, dollars, we may remove this as well since MOQ has many dimensions
7. how is MOQ calculated or is it a constraint
8. how are pre/in/end season percentage computed, change markdown % to end of season %
9. what is egment cost, shall we remove it
10. the bar chart is useless, need somethins else or rather not display chart at all
11. when i put "yo bro" in what if scenario input, i got output " Perfect. Yes, 2, which is within 2-3. Use these terms: service level, safety stock,.", how to interpret that, how to handle these weird scenario inputs, maybe put in a constraint if user put unexpected phrases then do no generate a response and point user to what they may ask instead
12. in decision context i added "if sales are softer by 25% what is the best strategy" it have option to chase and two numbers "Upside: 880,000  |  Downside: 1,320,000" what does chase mean to user and what do these numbers mean
13. when i tap select button against a scenario, the message disappears, unsure what should user see and what to interpret

what more we should be doing
1. should we be showing sku level policy if user requests that
2. the numbers of DCC, safety stock etc may get benefit if there is a approve policy piece, this approves the policy interacts with downstream enterprise production systems like kafka database or PO creation product to make use of these policies
3. approve polciy would also transalte into determining the first set of purchase orders in units and dollars which also can be sent as an instruction to downstream systems

