# DevStack extras script to install Rally

# Save trace setting
XTRACE=$(set +o | grep xtrace)
set -o xtrace

source $DEST/rally/devstack/lib/rally

if [[ "$1" == "source" ]]; then
    # Initial source
    source $TOP_DIR/lib/rally
elif [[ "$1" == "stack" && "$2" == "install" ]]; then
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
