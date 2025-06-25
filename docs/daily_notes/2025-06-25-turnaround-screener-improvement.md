# Turnaround Screener Improvement

Date: June 25, 2025

## Changes Made

Today I improved the turnaround candidate screener to better identify companies that have genuinely "turned the corner" from financial difficulties, rather than those simply showing steady growth. The previous implementation was identifying established firms with steady growth rather than genuine recovery candidates.

### Key Enhancements

1. **More Focused EPS Turnaround Detection**
   - Now requires evidence of negative EPS in previous quarters that turns positive in recent quarters
   - Distinguishes between true turnarounds (negative→positive) and mere improvements in already positive metrics

2. **Revenue Recovery Pattern**
   - Now identifies transition from negative to positive YoY growth
   - Looks back 2 years (8 quarters) to establish proper historical context

3. **Margin Recovery Detection**
   - Now identifies when margins bottomed out and have since recovered
   - Requires significant improvement from the low point (≥10%)

4. **Balance Sheet Turnaround**
   - Now detects when cash was previously declining but is now growing
   - Identifies when debt was previously increasing but is now decreasing

5. **Enhanced Scoring System**
   - Higher weights for true negative→positive transitions
   - Lower weights for mere acceleration in already positive metrics
   - Minimum score threshold increased from 3 to 5

6. **Improved Summary Output**
   - Now shows the primary factor contributing to the turnaround classification
   - Displays the full reason/score breakdown for better insights
   - Sorts results with true turnarounds first, then by score

### Expected Impact

These changes should result in the screener identifying companies that have genuinely recovered from financial difficulty rather than simply showing steady growth. This will provide better value in identifying potential investment opportunities that others might overlook due to historical difficulties.

### Example Turnaround Patterns

Ideal candidates will show patterns like:
- EPS: -$0.25 → -$0.15 → -$0.05 → +$0.10 → +$0.25
- Revenue Growth YoY: -5% → -2% → +3% → +8%
- Margins: 15% → 12% → 10% → 13% → 16%
- Cash: Declining for several quarters, then recent increases
- Debt: Increasing for several quarters, then recent decreases

## Future Improvements

- Consider adding strength of balance sheet as a factor (debt-to-equity ratio improvements)
- Incorporate analyst estimate beats after previous misses
- Add historical stock price pattern recognition (bottoming pattern)
- Include relative industry performance comparison
