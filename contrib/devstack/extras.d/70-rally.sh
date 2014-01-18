# rally.sh - DevStack extras script to install Rally

if is_service_enabled rally; then
    if [[ "$1" == "source" ]]; then
        # Initial source
        source $TOP_DIR/lib/rally
    elif [[ "$1" == "stack" && "$2" == "install" ]]; then
        echo_summary "Installing Rally"
        install_rally
    elif [[ "$1" == "stack" && "$2" == "post-config" ]]; then
        echo_summary "Configuring Rally"
        configure_rally
        create_rally_accounts
    elif [[ "$1" == "stack" && "$2" == "extra" ]]; then
        echo_summary "Initializing Rally"
        init_rally
    fi
fi
