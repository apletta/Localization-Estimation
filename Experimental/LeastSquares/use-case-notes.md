# Use Case Notes
- While recursive least squares can be a solution for state estimation, superior solutions exist. It is important to understand the limitations of this model. The work here serves as a building block to understanding the Kalman Filter and more advanced SLAM estimators. Files are adapted from the Coursera course: [State Estimation and Localization for Self-Driving Cars](https://www.coursera.org/learn/state-estimation-localization-self-driving-cars/home/welcome).

## Advantages
- Conceptually easier
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
- Produces same results as Maximum Likelihood Estimator according to Central Limit Theroem
