

Based solely on `doc.txt`, here is what each option's Greek measures and how it relates to options pricing:

**Delta**
- Measures how much an option's price can be expected to move for every $1 change in the price of the underlying security or index (e.g., a Delta of 0.40 means the option's price will theoretically move $0.40 for every $1 move in the underlying).
- It is used in pricing/analysis in several ways:
  - Traders use Delta to predict whether an option will expire in-the-money (ITM) — a Delta of 0.40 is taken to mean roughly a 40% chance of being ITM at expiration (though this doesn't guarantee profitability).
  - Delta can be thought of as the number of shares of the underlying stock the option behaves like (a 0.40 Delta option gains/loses about as much as 40 shares for a $1 move).
  - Call options have positive Delta (0.00 to 1.00); at-the-money (ATM) calls are near 0.50, and Delta approaches 1.00 as calls get deeper ITM or as ITM calls near expiration (OOTM calls approach 0.00). Put options have negative Delta (0.00 to –1.00); ATM puts are near –0.50, and Delta approaches –1.00 as puts get deeper ITM or as ITM puts near expiration (OOTM puts approach 0.00).

**Gamma**
- Measures the rate of change in an option's Delta over time — specifically, the rate of change in Delta per $1 change in the price of the underlying stock. The document likens Delta to speed and Gamma to acceleration.
- Example from the document: if an option with a Delta of 0.40 moves $0.40 after a $1 move in the stock, the option is now deeper ITM and its Delta might rise to 0.55; the change from 0.40 to 0.55 (0.15) is the option's Gamma.
- Because Delta can't exceed 1.00, Gamma decreases as an option gets further ITM and Delta approaches 1.00 (less room for "acceleration" as you approach top speed).

**Theta**
- Tells you how much the price of an option should decrease each day as the option nears expiration, if all other factors remain the same. This price erosion over time is called time decay.
- Time-value erosion is not linear: erosion for ATM, slightly out-of-the-money, and ITM options generally increases as expiration approaches, while erosion for far out-of-the-money (OOTM) options generally decreases as expiration approaches.

**Vega**
- Measures the rate of change in an option's price per one-percentage-point change in the implied volatility of the underlying stock. (The document notes Vega is not a real Greek letter, but it tells you how much an option's price should move when the underlying's volatility increases or decreases.)
- Volatility is one of the most important factors affecting option value. A drop in Vega typically causes both calls and puts to lose value; an increase in Vega typically causes both to gain value.
- Neglecting Vega can cause you to overpay when buying options. All else equal, the document suggests buying options when Vega is below "normal" levels and selling when it is above "normal" levels — one way to judge this is comparing historical volatility to implied volatility.

**Rho**
- Measures the expected change in an option's price per one-percentage-point change in interest rates — i.e., how much the option's price should rise or fall if the risk-free interest rate (U.S. Treasury bills) increases or decreases.
- As interest rates increase, call option values generally increase and put option values usually decrease, so calls have positive Rho and puts have negative Rho. The document illustrates this with a stock trading exactly at its strike ($25): when rates are low, the price gap between the 25 calls and 25 puts is relatively small; as rates rise, the gap widens (calls become more expensive, puts less so).
- Rho is generally not a huge factor in option price, but should be considered if interest rates are expected to change (e.g., just before a Federal Open Market Committee meeting). LEAPS options are far more sensitive to interest-rate changes than shorter-term options.

**Implied volatility (not a Greek, but closely related)**
- Implied volatility is a strictly theoretical forecast of how volatile an underlying stock is expected to be in the future. While future moves can be forecast from historical volatility, the implied volatility reflected in an option's price is an inference based on other factors too, such as upcoming earnings reports, merger and acquisition rumors, and pending product launches.
- How it's used in pricing:
  - Figuring out exactly how volatile a stock will be at any given time is difficult, but implied volatility gives a sense of what assumptions market makers are using to determine their quoted bid and ask prices — making it a helpful proxy for gauging the market.
  - Higher-than-normal implied volatilities are usually more favorable for options sellers, while lower-than-normal implied volatilities are more favorable for option buyers, because volatility often reverts to its mean over time.
  - It is often provided on options trading platforms because it is typically more useful for traders to know how volatile a market maker thinks a stock will be than to estimate it themselves.
  - Implied volatility is usually not consistent across all options of a particular security or index, and is generally lowest for at-the-money and near-the-money options.