#!/bin/sh
# FIXME(andrekurilin): remove this file, when patch with proper fix in infra
# (https://review.openstack.org/#/c/240580/) will be merged
exec $(dirname $0)/rally_verify.py --compare