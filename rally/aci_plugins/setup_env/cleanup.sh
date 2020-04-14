#!/bin/bash

source demo-functions.sh

function usage {
    echo "$0: [-h]"
    echo "  -h, --help                             Display help message"
    echo "  -c, --cleanup PROJECT_NAME             Deletes *ALL* VMs and Networks from Project"

}

function main {
    if [ $# -eq 0 ] ; then
        usage
    else

        while [ "$1" != "" ]; do
            case $1 in
                -h | --help )    usage
                                 exit
                                 ;;
                -c | --cleanup ) delete_all ${@:2}
                                 exit
                                 ;;
                * )              usage
                                 exit 1
            esac
            shift
        done
    fi
}

main $*
