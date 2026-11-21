

Based solely on `doc.txt`, here is what each option's Greek measures and how it is used in options pricing, plus an explanation of implied volatility:

## Delta
- **What it measures:** How much an option's price can be expected to move for every $1 change in the price of the underlying security or index. A Delta of 0.40 means the option's price will theoretically move $0.40 for every $1 change in the underlying.
- **How it's used:**
  - Traders use Delta to predict whether an option will expire in-the-money (ITM) — a Delta of 0.40 is taken to mean roughly a 40% chance of expiring ITM (though this doesn't guarantee profitability).
  - It can be thought of as the number of shares of the underlying stock the option behaves like (a Delta of 0.40 means the option gains/loses about as much as 40 shares for a $1 move).
  - **Calls** have positive Delta (0.00 to 1.00); ATM calls are near 0.50, Delta approaches 1.00 as the option gets deeper ITM and as expiration approaches for ITM calls, while OOTM calls drift toward 0.00.
  - **Puts** have negative Delta (0.00 to –1.00); ATM puts are near –0.50, Delta approaches –1.00 as the option gets deeper ITM and as expiration approaches for ITM puts, while OOTM puts drift toward 0.00.

## Gamma
- **What it measures:** The rate of change in an option's Delta over time — specifically, the rate of change in Delta per $1 change in the price of the underlying stock. The document likens Delta to speed and Gamma to acceleration.
- **How it's used:** It shows how quickly Delta itself is changing. For example, if a $1 move in the stock takes an option's Delta from 0.40 to 0.55, the change of 0.15 is the option's Gamma. Because Delta can't exceed 1.00, Gamma decreases as an option gets further ITM and Delta approaches 1.00 (less room for "acceleration" as you approach top speed).

## Theta
- **What it measures:** How much an option's price should decrease each day as the option nears expiration, all else being equal — this price erosion over time is called time decay.
- **How it's used:** It quantifies time-value erosion, which is not linear: erosion for ATM, slightly OOTM, and ITM options generally increases as expiration approaches, while erosion for far OOTM options generally decreases as expiration approaches.

## Vega
- **What it measures:** The rate of change in an option's price per one-percentage-point change in the implied volatility of the underlying stock. (The document notes Vega is not a real Greek letter, but it tells you how much the option's price should move when the underlying's volatility rises or falls.)
- **How it's used:**
  - Volatility is one of the most important factors affecting option value.
  - A drop in Vega typically causes both calls and puts to lose value; an increase typically causes both to gain value.
  - Neglecting Vega can cause you to overpay when buying options. All else equal, consider buying options when Vega is below "normal" levels and selling when it's above "normal" levels — one way to judge this is comparing historical volatility to implied volatility (chart studies for both are available on StreetSmart Edge®).

## Rho
- **What it measures:** The expected change in an option's price per one-percentage-point change in interest rates — i.e., how much the option's price should rise or fall if the risk-free interest rate (U.S. Treasury bills) increases or decreases.
- **How it's used:**
  - As interest rates increase, call values generally increase and put values usually decrease, so calls have positive Rho and puts have negative Rho.
  - Example from the document: for a stock trading exactly at its $25 strike, the 25 calls might trade at $0.60 and the 25 puts at $0.50. When rates are low, the put-call price gap is relatively small; as rates rise, the gap widens (calls become more expensive, puts less so).
  - Rho is generally not a huge factor in option price, but should be considered when interest rates are expected to change, such as just before a Federal Open Market Committee (FOMC) meeting.
  - LEAPS options are far more sensitive to interest-rate changes than shorter-term options.

## Implied Volatility (not a Greek, but closely related)
- **What it is:** A forecast of how volatile an underlying stock is expected to be in the future — but strictly theoretical. While future moves can be forecast from historical volatility, the implied volatility reflected in an option's price is an inference based on other factors too, such as upcoming earnings reports, merger and acquisition rumors, and pending product launches.
- **How it's used:**
  - Figuring out exactly how volatile a stock will be at any given time is difficult, but implied volatility gives a sense of what assumptions market makers are using to determine their quoted bid and ask prices, making it a helpful proxy for gauging the market.
  - Higher-than-normal implied volatilities are usually more favorable for options sellers, while lower-than-normal implied volatilities are more favorable for option buyers, because volatility often reverts to its mean over time.
  - It is often provided on options trading platforms because it's typically more useful for traders to know how volatile a market maker thinks a stock will be than to estimate it themselves.
  - Implied volatility is usually not consistent across all options of a particular security or index, and is generally lowest for at-the-money and near-the-money options.