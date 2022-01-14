# Notes

Express features in terms of a z-score (standardized around 0 and scaled by
the standard deviation). Only, instead of `stdev` use **absolute mean
deviation**.

1. Compute the mean for all values in the column
2. Compute MD for each column: 

$$\textrm{MD} = \dfrac{1}{n-1} \sum_{i=1}^{n} | x_i - \bar{x} |$$

3. For each value in the column, compute the "z-score" as 
$$z = (value - mean) / MD$$
