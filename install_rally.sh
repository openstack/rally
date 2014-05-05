#!/usr/bin/env bash
#
# This script installs Rally.
# Specifically, it is able to install and configure
# Rally either globally (system-wide), or isolated in
# a virtual environment using the virtualenv tool.
#
# NOTE: The script assumes that you have the following
# programs already installed:
# -> Python 2.6 or Python 2.7


err() {
  echo "${0##*/}: $@" >&2
}

print_usage() {
  echo "Usage: ${0##*/} [-v | -h]"
  echo "Options:"
  echo "  -v: install Rally isolated in a virtual environment"
  echo "  -h: print this usage message and exit"
}

check_root() {
  local user=$(/usr/bin/id -u)
  if [ ${user} -ne 0 ]; then
    err "Only the superuser (uid 0) can use this script."
    exit 1
  fi
}

parse_arguments() {
  scope='system'
  while getopts ":vh" opt; do
    case ${opt} in
      v)
        scope='isolated'
        return
        ;;
      h)
        print_usage
        exit 0
        ;;
      *)
        err "An invalid option has been detected."
        print_usage
        exit 1
    esac
  done
}

init_variables() {
  RALLY_VIRTUALENV_DIR="/opt/rally"
  RALLY_CONFIGURATION_DIR="/etc/rally"

  GETPIPPY_FILE="/tmp/get-pip.py"
  PIP_SECURE_LOCATION="https://raw.github.com/pypa/pip/master/contrib/get-pip.py"
  TMP="`dirname \"$0\"`"
  TMP="`( cd \"${TMP}\" && pwd )`"

  if [ "${scope}" = "system" ]; then
    RALLY_DATABASE_DIR="/var/lib/rally/database"
  elif [ "${scope}" = "isolated" ]; then
    RALLY_DATABASE_DIR="${RALLY_VIRTUALENV_DIR}/database"
  else
    err "Unexpected value for the scope variable."
    exit 1
  fi
}

install_rhel_based_system_requirements() {
  local install_rally_dependencies='curl'
  local cryptography_dependencies='gcc libffi-devel python-devel openssl-devel gmp-devel'
  local external_dependencies='libxml2-devel libxslt1-devel' # dependencies from projects, which are used by rally
  yum -y install ${install_rally_dependencies} ${cryptography_dependencies} ${external_dependencies}
}

install_debian_based_system_requirements() {
  local install_rally_dependencies='curl'
  local cryptography_dependencies='build-essential libssl-dev libffi-dev python-dev'
  local external_dependencies='libxml2-dev libxslt1-dev' # dependencies from projects, which are used by rally
  apt-get -y install ${install_rally_dependencies} ${cryptography_dependencies} ${external_dependencies}
}

unsupported_os_system_requirements() {
  echo "Your system is currently unsupported by this installation script."
  echo "Currently supported systems: RHEL-based, Debian-based."
  echo "If you want to proceed, first install manually the following dependencies:"
  echo "gcc, libffi-devel, python-devel, openssl-devel, curl"
  while true; do
    read -p "Do you want to proceed with the installation of Rally? [Y/n]: " ans
    case ${ans} in
      [Yy]*) return ;;
      [Nn]*) exit 1 ;;
      *) echo "Invalid answer. Please answer yes or no." ;;
    esac
 done
}

install_system_requirements() {
  local rhel_based='/etc/redhat-release'
  local debian_based='/etc/debian_version'

  if [ -f ${rhel_based} ]; then
    install_rhel_based_system_requirements
  elif [ -f ${debian_based} ]; then
    install_debian_based_system_requirements
  else
    unsupported_os_system_requirements
  fi

  hash pip 2> /dev/null
  if [ $? -ne 0 ]; then
    curl -L -o ${GETPIPPY_FILE} ${PIP_SECURE_LOCATION}
    python ${GETPIPPY_FILE}
  fi
}

setup_virtualenv() {
  pip install -U virtualenv
  virtualenv ${RALLY_VIRTUALENV_DIR}
  source ${RALLY_VIRTUALENV_DIR}/bin/activate
}

install_rally_requirements() {
  pip install pbr
  pip install 'tox<=1.6.1'
}

install_rally() {
  cd ${TMP}
  python setup.py install
}

configure_rally() {
  mkdir -p ${RALLY_DATABASE_DIR} ${RALLY_CONFIGURATION_DIR}
  cp ${TMP}/etc/rally/rally.conf.sample ${RALLY_CONFIGURATION_DIR}/rally.conf
  sed -i "/#connection=<None>/a connection=sqlite:////${RALLY_DATABASE_DIR}/rally.sqlite" ${RALLY_CONFIGURATION_DIR}/rally.conf

  rally-manage db recreate
  chmod -R go+w ${RALLY_DATABASE_DIR}
}

print_virtualenv_notice() {
  echo "======================================================================"
  echo "Before every Rally session, activate the virtualenv of Rally:"
  echo "$ source ${RALLY_VIRTUALENV_DIR}/bin/activate"
  echo
  echo "You may put the following in your ~/.bashrc file for convenience:"
  echo "alias initrally='source ${RALLY_VIRTUALENV_DIR}/bin/activate'"
  echo "======================================================================"
}

print_information() {
  echo "======================================================================"
  echo "Information about your Rally installation:"
  echo " * Method: ${scope}"
  if [ "${scope}" = "isolated" ]; then
    echo " * Virtual Environment at: ${RALLY_VIRTUALENV_DIR}"
  fi
  echo " * Database at: ${RALLY_DATABASE_DIR}"
  echo " * Configuration file at: ${RALLY_CONFIGURATION_DIR}"
  echo "======================================================================"
}

main() {
  check_root
  parse_arguments "$@"
  init_variables
  install_system_requirements
  if [ "${scope}" = "isolated" ]; then setup_virtualenv; fi
  install_rally_requirements
  install_rally
  configure_rally
  if [ "${scope}" = "isolated" ]; then print_virtualenv_notice; fi
  print_information
  exit 0
}

main "$@"
