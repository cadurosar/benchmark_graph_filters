import time
import argparse
import numpy as np
import pickle as pkl
import os
from math import log
from citation import train_regression
from models import get_model
from utils import sgc_precompute, load_citation, set_seed
from args import get_citation_args
import torch
from hyperopt import fmin, tpe, hp, STATUS_OK, Trials

# Arguments
args = get_citation_args()

# setting random seeds
set_seed(args.seed, args.cuda)

# Hyperparameter optimization
if args.model == 'SGC':
    space = {'weight_decay' : hp.loguniform('weight_decay', log(1e-10), log(1e-4))}
else:
    raise NotImplemented
    # space = {'weight_decay' : hp.loguniform('weight_decay', log(1e-6), log(1e-2)),
    #          'lr': hp.loguniform('lr', log(1e-3), log(1e-1)),
    #          'dropout': hp.uniform('dropout', 0., 0.5)}

adj, features, labels, idx_train, idx_val, idx_test = load_citation(args.dataset, args.normalization, args.cuda, sigma=args.sigma)
if args.model == "SGC": features, precompute_time = sgc_precompute(features, adj, args.degree)

def sgc_objective(space):
    model = get_model(args.model, features.size(1), labels.max().item()+1, args.hidden, args.dropout, args.cuda)
    model, acc_val, _ = train_regression(model, features[idx_train], labels[idx_train], features[idx_val], labels[idx_val],
                                      args.epochs, space['weight_decay'], args.lr, args.dropout)
    print('weight decay: {:.2e} '.format(space['weight_decay']) + 'accuracy: {:.4f}'.format(acc_val))
    return {'loss': -acc_val, 'status': STATUS_OK}

best = fmin(sgc_objective, space=space, algo=tpe.suggest, max_evals=200)
print("Best weight decay: {:.2e}".format(best["weight_decay"]))

with open("sigma_tuning.txt", "a") as f:
    best_val = -sgc_objective(best)['loss']
    f.write("{}, {}, {}\n".format(args.degree, args.sigma, best_val))
# os.makedirs("./{}-tuning".format(args.model), exist_ok=True)
# path = '{}-tuning/{}-{}.txt'.format(args.model, args.dataset, args.sigma)
# with open(path, 'wb') as f: pkl.dump(best, f)
