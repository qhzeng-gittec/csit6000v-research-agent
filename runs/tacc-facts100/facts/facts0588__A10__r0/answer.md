

Based on `doc.txt`, here is what each option's Greek measures and how it relates to option pricing, plus the explanation of implied volatility.

## Delta
- **What it measures:** "Delta measures how much an option's price can be expected to move for every $1 change in the price of the underlying security or index." For example, "a Delta of 0.40 means the option's price will theoretically move $0.40 for every $1 change in the price of the underlying stock or index."
- **How it's used:** "Traders often use Delta to predict whether a given option will expire ITM. So, a Delta of 0.40 is taken to mean that at that moment in time, the option has about a 40% chance of being ITM at expiration." It can also be viewed as share-equivalence: "You can also think of Delta as the number of shares of the underlying stock the option behaves like."
- **Range:** "Call options have a positive Delta that can range from 0.00 to 1.00," while "Put options have a negative Delta that can range from 0.00 to –1.00." At-the-money call options "usually have a Delta near 0.50" (doc.txt), and at-the-money put options "usually have a Delta near –0.50" (doc.txt). Delta "will increase (and approach 1.00) as the option gets deeper ITM" for calls, and "decrease (and approach –1.00)" for puts.

## Gamma
- **What it measures:** "Where Delta is a snapshot in time, Gamma measures the rate of change in an option's Delta over time." The document compares "Delta as speed and Gamma as acceleration." "In practice, Gamma is the rate of change in an option's Delta per $1 change in the price of the underlying stock."
- **How it's used:** The document illustrates with an example: if an option with a Delta of 0.40 moves with the stock such that "the Delta is now 0.55. The change in Delta from 0.40 to 0.55 is 0.15—this is the option's Gamma."
- **Behavior:** "Because Delta can't exceed 1.00, Gamma decreases as an option gets further ITM and Delta approaches 1.00."

## Theta
- **What it measures:** "Theta tells you how much the price of an option should decrease each day as the option nears expiration, if all other factors remain the same. This kind of price erosion over time is known as time decay."
- **How it's used:** The document notes that "Time-value erosion is not linear, meaning the price erosion of at-the-money (ATM), just slightly out-of-the-money, and ITM options generally increases as expiration approaches, while that of far out-of-the-money (OOTM) options generally decreases as expiration approaches."

## Vega
- **What it measures:** "Vega measures the rate of change in an option's price per one-percentage-point change in the implied volatility of the underlying stock." The document notes that "While Vega is not a real Greek letter, it is intended to tell you how much an option's price should move when the volatility of the underlying security or index increases or decreases."
- **How it's used:** "Volatility is one of the most important factors affecting the value of options." "A drop in Vega will typically cause both calls and puts to lose value," and "An increase in Vega will typically cause both calls and puts to gain value." "Neglecting Vega can cause you to potentially overpay when buying options. All other factors being equal, when determining strategy, consider buying options when Vega is below 'normal' levels and selling options when Vega is above 'normal' levels. One way to determine this is to compare the historical volatility to the implied volatility."

## Rho
- **What it measures:** "Rho measures the expected change in an option's price per one-percentage-point change in interest rates. It tells you how much the price of an option should rise or fall if the risk-free interest rate (U.S. Treasury-bills)* increases or decreases."
- **How it's used:** "As interest rates increase, the value of call options will generally increase," while "As interest rates increase, the value of put options will usually decrease. For these reasons, call options have positive Rho and put options have negative Rho." The document adds that "Rho is generally not a huge factor in the price of an option, but should be considered if prevailing interest rates are expected to change, such as just before a Federal Open Market Committee (FOMC) meeting," and that "Long-Term Equity AnticiPation Securities® (LEAPS®) options are far more sensitive to changes in interest rates than are shorter-term options."

## Implied volatility (not a Greek)
- **What it is:** "Though not actually a Greek, implied volatility is closely related. Implied volatility is a forecast of how volatile an underlying stock is expected to be in the future—but it's strictly theoretical." Unlike a forecast based on historical volatility, "the implied volatility reflected in the price of an option is an inference based on other factors, too, such as upcoming earnings reports, merger and acquisition rumors, pending product launches, etc."
- **How it's used:** "Figuring out exactly how volatile a stock will be at any given time is difficult, but looking at implied volatility can give you a sense of what assumptions market makers are using to determine their quoted bid and ask prices. As such, implied volatility can be a helpful proxy in gauging the market."
- **Trading implications:** "Higher-than-normal implied volatilities are usually more favorable for options sellers, while lower-than-normal implied volatilities are more favorable for option buyers, because volatility often reverts back to its mean over time." It is "often provided on options trading platforms because it is typically more useful for traders to know how volatile a market maker thinks a stock will be than to try to estimate it themselves."
- **Pattern:** "Implied volatility is usually not consistent for all options of a particular security or index and will generally be lowest for at-the-money and near-the-money options."