#!/bin/sh

CONTAINER=$1

mkdir -p $CONTAINER/root/.ssh
cp ~/.ssh/authorized_keys $CONTAINER/root/.ssh/
