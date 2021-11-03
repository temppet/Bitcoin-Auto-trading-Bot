![header](https://capsule-render.vercel.app/api?type=slice&color=78E150&height=200&section=header&text=Auto%20Trading%20Bot&fontColor=282828&fontSize=60)
<br>
<h2>📚 Long Poistion Condition 📚</h2>
<p align="left">
  <h4>1. previous candle is positive candle</h4>
  <h4>2. 2 previous candle is negative candle</h4>
  <h4>3. RSI of 2 previous candle under RSI_OVERSOLD</h4>
  <h4>4. minimum price of previous & 2 previous candle < minumum price of the previous 28 candle</h4>
  <h4>5. RSI of 2 previous candle > lowest RSI of the previous 28 candle</h4>
</p>
<br>
<h2> 📚 Short Poistion Condition 📚</h2>
<p align="left">
  <h4>1. previous candle is negative candle</h4>
  <h4>2. 2 previous candle is positive candle</h4>
  <h4>3. RSI of 2 previous candle over RSI_OVERBOUGHT</h4>
  <h4>4. maximum price of previous & 2 previous candle < maximum price of the previous 28 candle</h4>
  <h4>5. RSI of 2 previous candle < highest RSI of the previous 28 candle</h4>
</p>
<br>
<h2> 📚 Other Condition 📚</h2>
<p align="left">
  <h4>1. Take Profit: +2% (Reduce only setting)</h4>
  <h4>2. Stop Loss: -1% (Set Stop Loss)</h4>
  <h4>3. Stop Loss Change Spot: +0.5%</h4>
  <h4>4. changed Stop Loss Spot: +0.08%</h4>
  <br>
  <h4>5. Strategy : Trading through RSI divergence, trading at the moment the bar changes</h4>
  <br>
  <h4>6. Send by Naver mail for each contract</h4>
  <h4>7. Logging when an exception occurs(Mail cannot be sent. If it is a network error, - <br>
  <h4>&nbsp;&nbsp;&nbsp;&nbsp;an exception will occur during exception handling and the program will be terminated.)<br>
</p>

<br>
<br>

![footer](https://capsule-render.vercel.app/api?type=slice&color=B21EF1&height=100&section=footer)
