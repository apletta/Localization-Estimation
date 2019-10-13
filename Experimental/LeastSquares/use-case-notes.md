# Use Case Notes

## Advantages
- Conceptually easy
- Relatively fast processing time
- Can combine measurements from different sources (i.e. with different variance)
- Recursive solution can be used on live data

## Assumptions
- Linear model
- Gaussian variance for measurements

## Limitations
- Linear model
- Sensitive to outliers

## Other
- Explored as building block to Kalman Filter/more advanced SLAM estimators
- Produces same results as Maximum Likelihood Estimator according to Central Limit Theroem
