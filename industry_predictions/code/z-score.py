import pandas as pd
import numpy as np

train = pd.read_csv('hs300_features.csv', header=None, names=['code','name','industry'] + [f'f{i}' for i in range(27)])
test = pd.read_csv('test_features.csv', header=None, names=['code','name'] + [f'f{i}' for i in range(27)])

feat_cols = [f'f{i}' for i in range(27)]
mean = train[feat_cols].mean()
std = train[feat_cols].std().replace(0, 1e-8)

train[feat_cols] = (train[feat_cols] - mean) / std
test[feat_cols] = (test[feat_cols] - mean) / std

train.to_csv('train_standardized.csv', index=False, header=False)
test.to_csv('test_standardized.csv', index=False, header=False)