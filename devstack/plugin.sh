# DevStack extras script to install Rally

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

DIR=$(dirname ${BASH_SOURCE[0]})
source $DIR/lib/rally

MESSAGE="'rally git://git.openstack.org/openstack/rally' devstack plugin is
 deprecated and will be removed soon! Use 'rally-openstack
 git://git.openstack.org/openstack/rally-openstack' instead."
deprecated "$MESSAGE"

if [[ "$1" == "stack" && "$2" == "install" ]]; then
    echo_summary "Installing Rally"
    install_rally
elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
    echo_summary "Configuring Rally"
    configure_rally
elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
    echo_summary "Initializing Rally"
    init_rally
fi

# Restore xtrace
$XTRACE
