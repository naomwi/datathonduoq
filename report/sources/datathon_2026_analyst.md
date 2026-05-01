1

2

3

4

5

6

7

8

9

10

1 Revenue Anatomy: Where Does Revenue Come From?

To understand the drivers of business performance, we first examine the structure of revenue across
time, product categories, geographic regions, and customer channels. This section provides a
descriptive overview of how revenue is generated and highlights key patterns that motivate further
diagnostic investigation.

1.1 Temporal Trends and Seasonality

Figure 1 shows that revenue increased strongly from 2012 and reached its highest level around
2017–2018. However, after this peak period, revenue declined noticeably from 2019 onward. The
daily revenue trend also shows large spikes, suggesting that revenue is highly volatile and may be
influenced by short-term events such as promotional campaigns or seasonal demand.

(a) Daily revenue trend

(b) Monthly revenue trend

Figure 1: Revenue increased until 2017–2018, followed by a clear decline after 2019.

11

12

13

14

The monthly seasonality pattern in Figure 2 is particularly clear. Average revenue peaks between
April and June, with May being the strongest month, while revenue is lowest during the year-end
period. This pattern is repeated across multiple years, indicating that demand is strongly seasonal
rather than random.

(a) Average revenue by month

(b) Year-over-year monthly revenue

Figure 2: Revenue shows strong seasonality, with consistent peaks in April–June.

15

16

17

18

Weekly behavior further shows that revenue tends to be higher during the middle of the week,
especially on Wednesday and Thursday, while weekends generate lower average revenue. This
suggests that customer purchasing behavior is more active during weekdays, possibly due to marketing
schedules or browsing behavior during working days.

1

Figure 3: Average revenue by day of week. Mid-week days generate higher revenue than weekends.

19

20

21

22

Overall, the temporal analysis reveals two important findings. First, the business experienced rapid
but unsustained growth, with a clear decline after 2018. Second, revenue is highly seasonal, meaning
that planning for inventory, marketing, and logistics should be aligned with predictable demand
cycles.

23

1.2 Product Contribution

24

25

26

Revenue is highly concentrated in a single product category. As shown in Figure 4, Streetwear
overwhelmingly dominates total revenue, while Outdoor, Casual, and GenZ contribute much smaller
shares. This indicates that the company relies heavily on one category as its main revenue engine.

(a) Revenue by product category

(b) Revenue by product segment

Figure 4: Revenue is concentrated in Streetwear and mass-market segments.

27

28

29

30

31

32

33

At the segment level, revenue is mainly driven by Everyday and Balanced products. Premium, Trendy,
and Standard segments generate much smaller revenue. This suggests that the business is primarily
volume-driven and focused on mainstream products rather than high-margin or niche segments.

The category mix over time in Figure 5 confirms that Streetwear remains dominant throughout the
observation period. The lack of meaningful change in product mix suggests limited diversification
over time. This creates a concentration risk: if demand for Streetwear weakens, the overall business
would be highly exposed.

2

Figure 5: Revenue mix by category over time. Streetwear remains the dominant category across the
full period.

Therefore, while Streetwear is the strongest growth engine, the company should consider diversifying
its revenue base by developing secondary categories with growth potential. This would reduce
dependence on one product category and improve long-term business resilience.

1.3 Geographic Distribution

Revenue is also unevenly distributed across regions. Figure 6 shows that the East region contributes
the largest share of revenue, followed by Central and West. This suggests that market demand or
business penetration is strongest in the East.

(a) Revenue by region

(b) Top 10 cities by revenue

Figure 6: Revenue is regionally concentrated, but top-city revenue is relatively balanced.

At the city level, revenue among the top cities is relatively balanced. This reduces dependency on
any single city, but the regional imbalance still suggests that there may be underdeveloped markets,
particularly in the West. From a business perspective, the company could investigate whether lower
revenue in the West is caused by weaker demand, lower marketing reach, poorer logistics coverage,
or lower conversion rates.

1.4 Channel and Customer Behavior

Channel analysis shows that mobile devices generate the highest revenue, followed by desktop, while
tablet revenue is much smaller. This confirms that mobile is the primary transaction platform and
should be treated as a core business channel.

3

34

35

36

37

38

39

40

41

42

43

44

45

46

47

48

49

(a) Device type

(b) Order source

(c) Payment method

Figure 7: Mobile, organic search, and credit card payments are the dominant channels.

Organic search is the largest order source by revenue, followed by paid search and social media. This
indicates that search visibility is a major demand driver. However, reliance on organic search also
means that changes in search ranking or customer search behavior could significantly affect revenue.
Paid search and social media remain important supporting channels, but their efficiency should be
further evaluated through conversion and return analysis.

Payment behavior is strongly concentrated in credit card transactions. This suggests that customers
are comfortable with digital payments, which supports scalable online operations. However, other
payment methods such as COD and bank transfer contribute less revenue and should be evaluated
later in terms of cancellation rate and operational risk.

Finally, decomposing revenue into order volume and average order value reveals a critical pattern. As
shown in Figure 8, monthly order count drops sharply after 2018, while average order value increases
over time. This means that the post-2018 revenue decline is mainly driven by fewer transactions
rather than lower basket value.

(a) Monthly order count

(b) Monthly average order value

Figure 8: Order volume declines after 2018, while AOV increases over time.

This is one of the most important findings in the revenue anatomy analysis. The company is not
primarily losing revenue because customers spend less per order; instead, it appears to be losing
order volume. This points to potential issues in customer acquisition, retention, traffic quality, or
conversion efficiency, which should be investigated in the next section.

1.5 Summary of Key Findings

The revenue anatomy analysis highlights four major findings. First, revenue grew strongly until
2017–2018 but declined significantly after 2019, indicating that growth was not sustained. Second,
revenue is highly seasonal, with consistent peaks in April–June. Third, the business is heavily
dependent on Streetwear and mass-market product segments, creating product concentration risk.
Fourth, the decline in revenue after 2018 is mainly associated with falling order volume despite rising
AOV.

These findings suggest that the company should not only focus on increasing basket value, but also
investigate why order volume has weakened. The next section therefore examines potential drivers
behind the revenue decline, including marketing effectiveness, traffic behavior, promotions, and
operational frictions.

4

50

51

52

53

54

55

56

57

58

59

60

61

62

63

64

65

66

67

68

69

70

71

72

73

74

75

76

77

78

2 Driver Analysis: Why Did Revenue Decline After 2018?

79

80

81

82

83

The revenue anatomy in the previous section shows that the business experienced a clear decline
after 2018. More importantly, the decline appears to be driven by falling order volume, even though
average order value increased over time. This motivates a diagnostic question: why did fewer visits
become orders after 2018? In this section, we examine traffic, conversion, promotion activity, and
channel quality to identify the main drivers behind the revenue decline.

84

2.1 Traffic Growth Did Not Translate into Order Growth

85

86

87

88

89

90

91

Figure 9 compares indexed revenue, order count, sessions, and conversion proxy over time. All
metrics are normalized to the first observed month, allowing us to compare their relative movement
despite different units.

The most important pattern is that sessions increased substantially after 2018, while both revenue and
order count declined. This indicates that the business was still able to attract visitors, but became less
effective at converting those visitors into paying customers. In other words, the post-2018 decline is
not primarily a traffic acquisition problem, but a conversion problem.

Figure 9: Indexed traffic, orders, revenue, and conversion over time. Sessions increased after 2018,
while orders and revenue declined, indicating a conversion efficiency problem.

92

93

94

95

This pattern becomes clearer in Figure 10. Conversion proxy, defined as orders divided by sessions,
declined sharply after 2018. In the earlier period, conversion was typically around 1.0–1.2%, while
after 2019 it dropped to approximately 0.3–0.4%. This collapse directly explains why order volume
fell despite higher traffic.

5

Figure 10: Monthly conversion proxy, calculated as orders divided by sessions. Conversion declined
sharply after 2018.

96

97

98

99

100

Table 1 summarizes the magnitude of the change between the growth period and the post-2018
period. Average monthly sessions increased by 31.0%, but average monthly orders declined by 52.9%.
Meanwhile, average conversion proxy fell by 64.7%, making it the strongest negative driver. AOV
increased by 24.4%, confirming that the business was not losing revenue because customers spent
less per order, but because fewer visits converted into transactions.

Table 1: Driver changes after 2018.

Metric

Change: 2019–2022 vs. 2012–2018

Average monthly revenue
Average monthly orders
Average monthly sessions
Average conversion proxy
Average order value
Average promotion share
Average discount rate

-41.46%
-52.87%
+31.01%
-64.67%
+24.36%
-0.17%
+0.12%

101

102

103

Figure 11 visualizes these changes. The contrast between increasing sessions and declining conversion
confirms that the key business issue is not visitor volume, but the quality and effectiveness of the
conversion funnel.

6

Figure 11: Percentage changes in key drivers after 2018. The largest negative change is the decline in
conversion proxy.

104

2.2 Promotion Did Not Explain the Revenue Decline

105

106

107

108

109

110

111

112

113

114

We next examine whether the revenue decline can be explained by changes in promotion intensity.
The data shows that average promotion share remained almost unchanged before and after 2018,
decreasing only slightly from 40.68% to 40.62%. Similarly, the average discount rate remained nearly
constant.

This suggests that the revenue decline was not caused by a reduction in promotional activity. Therefore,
simply increasing broad discounts is unlikely to solve the problem. The issue appears to be deeper:
the company attracted traffic, but failed to convert it efficiently.

Figure 12 further shows that promotional revenue remains heavily concentrated in Streetwear. This
means that promotions reinforce the existing dependence on the dominant category rather than
diversifying demand across the product portfolio.

Figure 12: Revenue by category for promo and non-promo transactions. Promotions remain concen-
trated in Streetwear, indicating limited demand diversification.

115

116

117

From a business perspective, this is important because Chapter A showed that Streetwear already
dominates total revenue. If promotions mainly strengthen Streetwear, they may improve short-term
sales but do not reduce product concentration risk. A better strategy would be to use Streetwear as an

7

118

119

anchor category to cross-sell Outdoor, Casual, or GenZ products through bundles, targeted vouchers,
or category-specific campaigns.

120

2.3 Channel Quality Explains Part of the Conversion Problem

121

122

123

124

Channel-level analysis provides additional evidence that not all traffic has equal commercial value.
Figure 13 shows revenue per session by traffic source. Organic search generates the largest traffic
volume and total revenue, but it has the lowest revenue per session. In contrast, social media generates
the highest revenue per session, suggesting stronger purchase intent or better audience-product fit.

Figure 13: Revenue per session by traffic source. Organic search has the lowest revenue per session,
while social media has the highest.

125

126

127

128

129

130

131

132

133

This finding changes the interpretation of channel performance. Organic search appears strong if
judged only by total revenue, but its low revenue per session suggests a traffic quality issue. The
company may be attracting many visitors through organic search, but these visitors may have lower
purchase intent or may be landing on pages that do not match their needs.

Therefore, the business should not focus only on increasing total traffic. Instead, it should improve
traffic quality and landing-page relevance, especially for organic search. Potential actions include
auditing SEO keywords, improving product-page matching, strengthening retargeting for organic
visitors, and reallocating investment toward channels with higher revenue per session if customer
acquisition cost remains reasonable.

134

2.4 Business Implications

135

136

137

138

139

140

141

142

143

144

145

146

The diagnostic analysis shows that the post-2018 decline is mainly caused by conversion deterioration.
Sessions increased by 31.0%, but conversion proxy declined by 64.7%, leading to a 52.9% decline
in monthly orders and a 41.5% decline in revenue. Since AOV increased by 24.4%, the issue is not
basket size. Since promotion share and discount rate remained almost unchanged, the issue is also
not insufficient discounting.

The main implication is that the company should prioritize conversion quality over traffic volume.
Recommended actions include auditing the full funnel from landing page to checkout, analyzing
conversion by source and device, improving organic-search landing pages, and shifting from broad
promotions to targeted campaigns that support category diversification.

3 Operational Frictions: Where Is Revenue Being Lost?

The previous section shows that the post-2018 revenue decline is primarily driven by a sharp
deterioration in conversion efficiency. However, conversion is not only affected by marketing and

8

147

148

149

traffic quality. Operational frictions such as inventory stockouts, product returns, shipping experience,
and order cancellations can also prevent demand from becoming realized revenue. Therefore, this
section investigates where revenue may be lost after customers enter the purchase journey.

150

3.1

Inventory Constraints in the Core Category

151

152

153

154

155

156

157

Figure 14 shows total stockout days by product category. Streetwear has the highest stockout exposure,
with 36,993 total stockout days, followed by Outdoor with 23,552 days. GenZ and Casual have much
lower stockout exposure, with 5,368 and 4,012 days respectively.

This finding is important because Chapter A shows that Streetwear is the dominant revenue category.
Therefore, Streetwear is not only the main revenue engine but also the largest inventory risk point. If
customers arrive with purchase intent but key Streetwear products are unavailable, potential demand
may fail to convert into orders.

Figure 14: Total stockout days by category. Streetwear has the highest stockout exposure, making
inventory availability a potential constraint in the core revenue category.

158

159

160

161

However, average fill rates remain high and similar across categories, around 96%, as shown in
Figure 15. This suggests that the inventory problem is not a broad fulfillment failure across the entire
business. Instead, the issue is more likely concentrated in specific high-demand products, sizes, or
periods within the dominant categories.

9

Figure 15: Average fill rate by category. Fill rates are consistently high, but small gaps in high-volume
categories may still create meaningful lost sales.

From a business perspective, this means that the company should not only monitor average fill rate,
but also identify high-demand SKUs with repeated stockouts. Priority should be given to Streetwear
products with high sell-through rates, frequent stockout days, and strong historical sales. Improving
inventory availability in these products is likely to have a larger revenue impact than uniform inventory
expansion across all categories.

3.2 Returns Are Driven More by Fit and Expectation Issues Than by Category-Level

Satisfaction

Returns represent direct revenue leakage through refunded orders and additional operational costs.
Table 2 summarizes return behavior by category. GenZ has the highest return rate at 3.52%, followed
by Outdoor at 3.45%, Streetwear at 3.38%, and Casual at 3.26%. The differences are relatively small,
suggesting that no single category has a dramatically higher return rate.

Table 2: Return rate and refund amount by category.

Category

Return Rate Returned Items Refund Amount

GenZ
Outdoor
Streetwear
Casual

3.52%
3.45%
3.38%
3.26%

5,873
40,417
59,812
3,499

11.15M
78.72M
406.77M
14.03M

Although GenZ has the highest return rate, Streetwear generates the largest absolute return volume
and refund amount because of its much larger sales scale. This creates two different business
priorities: GenZ should be monitored for product-quality risk, while Streetwear should be prioritized
for reducing financial leakage.

The strongest return insight comes from return reasons. Figure 16 shows that wrong size is the leading
return reason, with 13,967 return records and approximately 176.7M in refunds. This is followed
by defective, not as described, and changed mind. Late delivery is the least common among the top
return reasons.

10

162

163

164

165

166

167

168

169

170

171

172

173

174

175

176

177

178

179

180

Figure 16: Top return reasons. Wrong size is the largest source of returns and refund amount,
suggesting a product-fit and expectation alignment issue.

181

182

183

184

185

This suggests that return leakage is driven more by product-fit and expectation mismatch than by
broad dissatisfaction with a specific category. The company should therefore prioritize better sizing
guidance, fit recommendations, clearer product descriptions, and product-quality control. In particular,
size guides, model references, customer fit reviews, and “runs small/runs large” warnings could
reduce wrong-size returns.

186

3.3 Delivery Time Does Not Appear to Be the Main Return Driver

187

188

189

We also examine whether logistics friction explains return behavior. Figure 17 shows return rate by
delivery-time bucket. Return rates remain very similar across delivery times: 6.46% for 2–3 days,
6.35% for 4–5 days, and 6.30% for 6–7 days.

Figure 17: Return rate by delivery time bucket. Return rates do not increase with longer delivery
time, suggesting that delivery speed is not the main driver of returns.

190

191

192

193

This evidence does not support the hypothesis that longer delivery times are causing higher return
rates. This is also consistent with the return-reason analysis, where late delivery is the smallest major
return reason. Therefore, if the business aims to reduce returns, product-fit and expectation issues
should be prioritized before logistics speed.

11

194

3.4 Review Ratings Are Stable Across Categories

195

196

197

Review ratings provide another view of post-purchase experience. Figure 18 shows that the rating
distribution is highly similar across categories. Across all categories, 4-star and 5-star reviews account
for roughly 71–72% of total reviews, while 1-star and 2-star reviews represent only around 13%.

Figure 18: Review rating distribution by category. Rating distributions are very similar across
categories, indicating no severe category-level satisfaction gap.

198

199

200

201

202

This suggests that there is no severe category-level satisfaction gap. Importantly, review records
do not overlap with return records at the item level, so we do not infer a direct causal relationship
between review rating and return behavior. Instead, we analyze reviews and returns separately.
Reviews suggest stable overall satisfaction, while returns indicate that revenue leakage is more related
to specific product-fit and expectation issues.

203

3.5 COD Creates a Major Cancellation Risk

204

205

206

Finally, we examine order cancellations. Figure 19 shows that cash-on-delivery (COD) has a
cancellation rate of around 16%, which is nearly twice as high as other payment methods, which are
around 8%.

Figure 19: Cancellation rate by payment method. COD has a much higher cancellation rate than
digital payment methods, making it a major source of order-quality risk.

207

208

This is a major operational risk. COD may increase order accessibility, but it also creates weaker
customer commitment and higher cancellation probability. Cancelled COD orders can distort demand

12

209

210

211

212

213

214

forecasts, reserve inventory that could have been sold elsewhere, and increase operational handling
costs.

The company does not need to remove COD entirely, but it should manage COD risk more actively.
Possible actions include order confirmation before fulfillment, limiting COD for high-value baskets,
offering small incentives for prepaid payment, and applying risk scoring to COD orders based on
customer history, region, and order value.

215

3.6 Summary and Recommendations

216

217

218

219

220

221

222

223

224

225

226

Operational analysis identifies three main revenue leakage points. First, Streetwear has the highest
stockout exposure despite being the dominant revenue category, indicating that inventory availability
may constrain sales in the core business. Second, returns are driven primarily by wrong-size and
product-expectation issues rather than broad category-level dissatisfaction or delivery delay. Third,
COD has a cancellation rate nearly twice as high as other payment methods, making it a major
order-quality risk.

These findings suggest three actionable priorities. The company should improve inventory planning
for high-demand Streetwear SKUs, reduce wrong-size returns through better sizing and product
information, and manage COD risk through stronger confirmation and prepaid-payment incentives.
Together, these actions address operational frictions that may weaken conversion and reduce realized
revenue.

227

4 Prescriptive Strategy: What Should the Business Do?

228

229

230

231

232

233

234

The previous sections identify three major business problems. First, the revenue decline after 2018
is mainly driven by a collapse in conversion efficiency rather than a lack of traffic. Second, the
company remains highly dependent on Streetwear, which is both the dominant revenue category and
the category with the highest stockout exposure. Third, revenue leakage is driven by operational
frictions such as wrong-size returns and high COD cancellation.

Based on these findings, we propose a prescriptive strategy focused on improving conversion quality,
protecting the core revenue category, and reducing avoidable revenue leakage.

235

4.1 Prioritize Conversion Before Scaling Traffic

236

237

238

239

240

241

242

243

The most urgent recommendation is to improve conversion before increasing traffic acquisition. After
2018, average monthly sessions increased by 31.0%, but average monthly orders declined by 52.9%,
while conversion proxy fell by 64.7%. This shows that the company is attracting visitors but failing
to convert them into buyers.

Therefore, the company should audit the full purchase funnel, including landing pages, product pages,
cart behavior, and checkout completion. Conversion should also be analyzed by traffic source, device
type, and product category. In particular, organic search should be prioritized because it generates the
largest traffic volume but the lowest revenue per session.

244

4.2

Improve Traffic Quality, Especially Organic Search

245

246

247

248

249

250

251

Organic search generates the largest total traffic and revenue, but it has the lowest revenue per session.
This suggests that organic traffic may contain many low-intent visitors or that landing pages do not
match customer intent well enough.

The company should audit SEO keywords, improve keyword-to-product matching, optimize landing
pages for high-intent queries, and retarget organic visitors who browse products but do not purchase.
Channel performance should be evaluated not only by total revenue, but also by conversion proxy
and revenue per session.

13

252

4.3 Protect Streetwear Inventory

253

254

255

256

257

258

259

Streetwear is the company’s dominant revenue category, but it also has the highest stockout exposure,
with 36,993 total stockout days. This makes Streetwear both the main growth engine and a major
inventory risk point.

The company should prioritize inventory planning for high-demand Streetwear SKUs, especially
before seasonal peaks in April–June. Instead of only monitoring category-level fill rate, the business
should track stockout days, sell-through rate, and days of supply at the SKU, size, and color level.
This would help prevent lost sales in the category that matters most to revenue.

260

4.4 Reduce Wrong-Size Returns

261

262

263

264

265

266

267

Return analysis shows that wrong size is the leading return reason, with 13,967 return records and
approximately 176.7M in refunds. Since return rates are similar across sizes, the issue is less likely to
be one specific size and more likely to be sizing guidance and expectation mismatch.

The company should improve size guides, add fit recommendations, include model references, and
surface customer reviews related to fit. Product pages should also include warnings such as “runs
small” or “runs large” when applicable. Reducing wrong-size returns would directly reduce refund
leakage and improve post-purchase satisfaction.

268

4.5 Control COD Cancellation Risk

269

270

271

272

273

274

275

COD has a cancellation rate of approximately 16%, nearly twice that of other payment methods.
While COD can increase accessibility, it also creates weaker customer commitment and higher
order-quality risk.

The company should not remove COD entirely, but should manage it more carefully. Recommended
actions include confirming COD orders before fulfillment, limiting COD availability for high-value
baskets, offering small incentives for prepaid payments, and applying risk scoring based on customer
history, order value, and region.

Problem

Table 3: Recommended business actions based on EDA findings.
Key Metrics

Recommended Action

Conversion decline

Audit landing page, product page,
cart, and checkout funnel

Low organic-search effi-
ciency
Streetwear stockout risk

Wrong-size returns

Improve keyword intent matching
and landing-page relevance
Prioritize replenishment for high-
demand Streetwear SKUs
Improve size guide, fit recommenda-
tion, and product description

High COD cancellation Confirm COD orders and incentivize

prepaid payment

rev-
checkout

Conversion proxy,
enue/session,
completion
Organic revenue/session,
organic conversion proxy
Stockout days, fill rate,
sell-through rate
Wrong-size return count,
refund amount
COD cancellation rate,
prepaid payment share

276

4.6 Summary

277

278

279

280

281

The recommended strategy is not to increase traffic or discounts indiscriminately. Instead, the com-
pany should focus on converting existing traffic more effectively, improving organic-search quality,
protecting Streetwear inventory, reducing wrong-size returns, and controlling COD cancellation risk.
These actions directly address the main drivers identified in the EDA and provide a more sustainable
path to revenue recovery.

14

