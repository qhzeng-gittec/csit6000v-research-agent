

I've read the entire `doc.txt` (120 lines) and searched it for any mention of spreads, credit strategies, defined risk, or Apple. Here is my answer based only on that document:

**Important caveat first:** The document never mentions put credit spreads, Apple, or the phrase "defined risk." It discusses only single, "uncovered" option positions. So I cannot confirm from this article that a put credit spread would truly have defined risk or prevent assignment. What the document *does* say about short puts — the assignment-exposed leg of your spread — is directly relevant, and it does not support the idea that you would avoid being assigned shares.

**What the document says about short puts and assignment:**

1. **Sellers have no control over assignment.** "When you sell an option, you may be assigned—at any time regardless of the ITM amount—if the option owner chooses to exercise. The option seller has no control over assignment and no certainty as to when it could happen. Once the assignment notice is delivered, it's too late to close the position."

2. **A short put, when ITM, is typically assigned.** The document's table states that when the underlying stock price is lower than the strike price, "a short put is... ITM and typically assigned." If the stock is higher than the strike, it is "OTM and typically abandoned."

3. **Assignment on a short put means buying the stock.** The document is explicit: "A short put assignment results in buying the underlying stock at the strike price." Each standard equity option contract controls 100 shares, so assignment converts your option position into actual shares.

4. **Automatic exercise makes this near-certain when ITM.** "If an option is ITM by as little as $0.01 at expiration, it will automatically be exercised for the buyer and assigned to a seller." The only escape is a rare "do not exercise" (DNE) request from the option holder.

5. **If you're uncovered, you end up owning the stock and need cash.** "If an option on XYZ is exercised or assigned and you are 'uncovered' (you don't have an existing long or short position in the underlying security), a long or short position in the underlying stock will replace the options. A long call or short put will result in a long position in XYZ." And: "For long stock positions, you need to have enough cash to cover the purchase or else you'll be issued a margin call," which the broker can force you to meet, with the right to liquidate your account positions.

6. **Pin risk adds uncertainty.** If the stock settles exactly at the strike, "you may or may not be assigned—and you may not be able to trade out of any unwanted positions until the next business day."

7. **You may not even be able to close out.** "There is no guarantee that there will be an active market for an options contract, so it is possible to end up stuck and unable to close an options position."

**Conclusion based solely on this document:** If you sell a put and Apple closes below your short put's strike at expiration, the document says that put is ITM and typically assigned, and assignment results in *buying* the stock at the strike price — the opposite of your goal of not owning the shares. The document provides no description of a long put leg capping losses or offsetting assignment, so it cannot confirm that a put credit spread has "defined risk" or prevents assignment. On the basis of this article alone, the strategy you describe would not be verified as assignment-proof; you should seek a source that actually covers credit spreads before trading.