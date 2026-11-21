

Based solely on `doc.txt`, here is what each Greek measures and how it relates to options pricing:

**Delta**
- Measures how much an option's price can be expected to move for every $1 change in the price of the underlying security or index. A Delta of 0.40 means the option's price will theoretically move $0.40 for every $1 change in the underlying. The higher the Delta, the bigger the price change.
- It can also be thought of as the number of shares of the underlying stock the option behaves like (a Delta of 0.40 means the option gains or loses about the same amount as 40 shares for a $1 move).
- Traders use Delta to predict whether an option will expire ITM: a Delta of 0.40 is taken to mean about a 40% chance of being ITM at expiration (though this doesn't guarantee profitability).
- Call options have a positive Delta ranging from 0.00 to 1.00 (ATM near 0.50; approaches 1.00 as the option gets deeper ITM and as ITM calls near expiration; OOTM calls approach 0.00 as expiration approaches). Put options have a negative Delta ranging from 0.00 to –1.00 (ATM near –0.50; approaches –1.00 as the option gets deeper ITM and as ITM puts near expiration; OOTM puts approach 0.00 as expiration approaches).

**Gamma**
- Where Delta is a snapshot in time, Gamma measures the rate of change in an option's Delta over time — specifically, the rate of change in Delta per $1 change in the price of the underlying stock. The document compares Delta to speed and Gamma to acceleration.
- Example from the document: if an option with a Delta of 0.40 moves with a $1 stock move and its Delta becomes 0.55, the change of 0.15 is the option's Gamma.
- Because Delta can't exceed 1.00, Gamma decreases as an option gets further ITM and Delta approaches 1.00 (less room for "acceleration" as you approach top speed).

**Theta**
- Tells you how much the price of an option should decrease each day as the option nears expiration, if all other factors remain the same. This price erosion over time is known as time decay.
- Time-value erosion is not linear: erosion for ATM, slightly OOTM, and ITM options generally increases as expiration approaches, while erosion for far OOTM options generally decreases as expiration approaches.

**Vega**
- Measures the rate of change in an option's price per one-percentage-point change in the implied volatility of the underlying stock. It tells you how much an option's price should move when the volatility of the underlying security or index increases or decreases. (The document notes Vega is not a real Greek letter.)
- Volatility is one of the most important factors affecting the value of options. A drop in Vega typically causes both calls and puts to lose value; an increase in Vega typically causes both to gain value.
- Neglecting Vega can cause you to overpay when buying options. All else equal, the document suggests considering buying options when Vega is below "normal" levels and selling when it is above "normal" levels, one way to determine this being by comparing historical volatility to implied volatility.

**Rho**
- Measures the expected change in an option's price per one-percentage-point change in interest rates — how much the option's price should rise or fall if the risk-free interest rate (U.S. Treasury-bills) increases or decreases.
- As interest rates increase, call option values generally increase and put option values usually decrease, so calls have positive Rho and puts have negative Rho. The document's example: with a stock at its $25 strike, 25 calls at $0.60 and 25 puts at $0.50, low interest rates keep the put-call price difference relatively small, while rising rates widen the gap (calls more expensive, puts less so).
- Rho is generally not a huge factor in an option's price, but should be considered if prevailing interest rates are expected to change, such as just before a Federal Open Market Committee (FOMC) meeting. LEAPS options are far more sensitive to interest-rate changes than shorter-term options.

**Implied volatility (not a Greek, but closely related)**
- Implied volatility is a forecast of how volatile an underlying stock is expected to be in the future — but it's strictly theoretical. While a stock's future moves can be forecast from its historical volatility among other factors, the implied volatility reflected in the price of an option is an inference based on other factors too, such as upcoming earnings reports, merger and acquisition rumors, and pending product launches.
- Figuring out exactly how volatile a stock will be at any given time is difficult, but implied volatility gives a sense of what assumptions market makers are using to determine their quoted bid and ask prices, making it a helpful proxy in gauging the market.
- Higher-than-normal implied volatilities are usually more favorable for options sellers, while lower-than-normal implied volatilities are more favorable for option buyers, because volatility often reverts back to its mean over time.
- Implied volatility is often provided on options trading platforms because it is typically more useful for traders to know how volatile a market maker thinks a stock will be than to try to estimate it themselves.
- Implied volatility is usually not consistent for all options of a particular security or index and will generally be lowest for at-the-money and near-the-money options.