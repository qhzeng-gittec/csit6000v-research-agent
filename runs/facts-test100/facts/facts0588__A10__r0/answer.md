

Based on `doc.txt`, here is what each Greek measures and how it is used in options pricing:

**Delta**
- What it measures: "Delta measures how much an option's price can be expected to move for every $1 change in the price of the underlying security or index." (doc.txt)
- How it's used: "Traders often use Delta to predict whether a given option will expire ITM. So, a Delta of 0.40 is taken to mean that at that moment in time, the option has about a 40% chance of being ITM at expiration." (doc.txt) It can also be viewed as share-equivalence: "You can also think of Delta as the number of shares of the underlying stock the option behaves like." (doc.txt)
- Call options "have a positive Delta that can range from 0.00 to 1.00," while put options "have a negative Delta that can range from 0.00 to –1.00." (doc.txt)

**Gamma**
- What it measures: "Gamma measures the rate of change in an option's Delta over time." (doc.txt) More precisely, "In practice, Gamma is the rate of change in an option's Delta per $1 change in the price of the underlying stock." (doc.txt)
- How it's used: The document illustrates it with an example where an option's Delta moves from 0.40 to 0.55 after a $1 move in the stock, and "The change in Delta from 0.40 to 0.55 is 0.15—this is the option's Gamma." (doc.txt) It also notes that "Because Delta can't exceed 1.00, Gamma decreases as an option gets further ITM and Delta approaches 1.00." (doc.txt)

**Theta**
- What it measures: "Theta tells you how much the price of an option should decrease each day as the option nears expiration, if all other factors remain the same. This kind of price erosion over time is known as time decay." (doc.txt)
- How it's used: The document notes that "Time-value erosion is not linear, meaning the price erosion of at-the-money (ATM), just slightly out-of-the-money, and ITM options generally increases as expiration approaches, while that of far out-of-the-money (OOTM) options generally decreases as expiration approaches." (doc.txt)

**Vega**
- What it measures: "Vega measures the rate of change in an option's price per one-percentage-point change in the implied volatility of the underlying stock." (doc.txt) It "is intended to tell you how much an option's price should move when the volatility of the underlying security or index increases or decreases." (doc.txt)
- How it's used: "A drop in Vega will typically cause both calls and puts to lose value. An increase in Vega will typically cause both calls and puts to gain value." (doc.txt) For strategy: "Neglecting Vega can cause you to potentially overpay when buying options. All other factors being equal, when determining strategy, consider buying options when Vega is below "normal" levels and selling options when Vega is above "normal" levels." (doc.txt)

**Rho**
- What it measures: "Rho measures the expected change in an option's price per one-percentage-point change in interest rates. It tells you how much the price of an option should rise or fall if the risk-free interest rate (U.S. Treasury-bills)* increases or decreases." (doc.txt)
- How it's used: "As interest rates increase, the value of call options will generally increase. As interest rates increase, the value of put options will usually decrease. For these reasons, call options have positive Rho and put options have negative Rho." (doc.txt) The document adds that "Rho is generally not a huge factor in the price of an option, but should be considered if prevailing interest rates are expected to change, such as just before a Federal Open Market Committee (FOMC) meeting," and that "Long-Term Equity AnticiPation Securities® (LEAPS®) options are far more sensitive to changes in interest rates than are shorter-term options." (doc.txt)

**Implied volatility (not a Greek, but closely related)**
- What it is: "Implied volatility is a forecast of how volatile an underlying stock is expected to be in the future—but it's strictly theoretical." (doc.txt) Unlike historical volatility, "the implied volatility reflected in the price of an option is an inference based on other factors, too, such as upcoming earnings reports, merger and acquisition rumors, pending product launches, etc." (doc.txt)
- How it's used in pricing: "looking at implied volatility can give you a sense of what assumptions market makers are using to determine their quoted bid and ask prices. As such, implied volatility can be a helpful proxy in gauging the market." (doc.txt)
- Practical implications: "Higher-than-normal implied volatilities are usually more favorable for options sellers, while lower-than-normal implied volatilities are more favorable for option buyers, because volatility often reverts back to its mean over time." (doc.txt) It is "often provided on options trading platforms because it is typically more useful for traders to know how volatile a market maker thinks a stock will be than to try to estimate it themselves." (doc.txt) Finally, "Implied volatility is usually not consistent for all options of a particular security or index and will generally be lowest for at-the-money and near-the-money options." (doc.txt)