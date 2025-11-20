# **Average bar price movement = ATR (Average True Range)**

ATR is the canonical indicator for:

* **Average bar movement size**
* **Average intraday volatility**
* **Average “candle size” over time**

And it is the **standard denominator** for normalizing current price movement.

If you want:

[
\frac{\text{current price change}}{\text{average bar movement}}
]

the **correct denominator is ATR** (or true range, TR, for a single bar).

---

# **1. True Range (TR): per-bar volatility**

For each bar:

[
\text{TR}*t = \max{
H_t - L_t,,
|H_t - C*{t-1}|,,
|L_t - C_{t-1}|
}
]

This captures gap-ups/gap-downs and is the most realistic definition of *bar movement*.

---

# **2. Average True Range (ATR): average bar movement**

ATR is simply:

[
\text{ATR}*t = \operatorname{EMA}*{n}(\text{TR}_t)
]

Typically (n = 14) or 20.

ATR gives you:

* Typical daily range
* Typical bar volatility
* A smoothing that behaves well across market regimes

---

# **3. The ratio you are asking for**

This is a standard volatility-normalized measure:

[
\frac{|C_t - C_{t-1}|}{\text{ATR}_t}
]

Interpretation:

* **< 0.3** → small move; noise
* **0.5 – 1.0** → normal move
* **1.0 – 2.0** → large move vs normal
* **> 2.0** → outsized move; unusual volatility
* **> 3.0** → significant event (news, earnings, liquidation cascade)

This ratio is used in:

* Breakout systems
* Trend filters
* Volatility normalization
* Position sizing
* Risk models (e.g., turtle rules, keltner-based entries)

---

# **4. The formal name for the ratio**

There isn’t a “classic” name, but quants usually refer to it as:

* **Volatility-normalized return**
* **ATR-normalized return**
* **True-range normalized move**
* **Normalized price change**

In code libraries like *pandas-ta* or *TA-Lib*, you simply compute:

```python
return_norm = (close.diff()) / atr
```

---

# **5. Are there alternatives?**

Yes, but ATR is by far the most widely accepted. Alternatives include:

### **a) Standard deviation of returns (volatility)**

[
\frac{r_t}{\sigma_{r}}
]
But this is backward-looking and doesn’t capture intraday ranges.

### **b) Average Range (AR)**

Simple average of (H_t - L_t), but ATR is strictly better.

### **c) Parkinson volatility**

Uses only high/low for “range-based vol”:
[
\sigma_P = \frac{1}{4 \ln 2}( \ln(H/L) )^2
]
More academically pure, but less practical for trading engines.

---

# **6. What’s best for your MC/backtesting engine?**

**ATR is the right choice** because:

1. **It works on any timeframe**
2. **It incorporates gaps**
3. **It’s robust in noisy environments**
4. **It’s widely used for position sizing** (you’re doing daily $500–$1000 targets)
5. **It’s stable under Monte Carlo**, while standard deviation can be unstable with small windows.

**Conclusion: Use ATR** as your measure of “average bar price movement”
and use:

[
\text{normalized_move} = \frac{|C_t - C_{t-1}|}{\text{ATR}_t}
]

If you want, I can help you:

* Add ATR to your `features/feature_engineering.py`,
* Add normalized-move as a feature,
* Add thresholds for candidate selection or strategies.
