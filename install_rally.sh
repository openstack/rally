#!/usr/bin/env bash
#
# This script installs Rally.
# Specifically, it is able to install and configure
# Rally either globally (system-wide), or isolated in
# a virtual environment using the virtualenv tool.
#
# NOTE: The script assumes that you have the following
# programs already installed:
# -> Python 2.6, Python 2.7 or Python 3.4

set -e

PROG=$(basename "${0}")

running_as_root() {
  test "$(/usr/bin/id -u)" -eq 0
}

VERBOSE=""
ASKCONFIRMATION=1
RECREATEDEST="ask"
USEVIRTUALENV="yes"
DEVELOPMENT_MODE="false"

# ansi colors for formatting heredoc
ESC=$(printf "\e")
GREEN="$ESC[0;32m"
NO_COLOR="$ESC[0;0m"
RED="$ESC[0;31m"

PYTHON2=$(which python || true)
PYTHON3=$(which python3 || true)
PYTHON=${PYTHON2:-$PYTHON3}
BASE_PIP_URL=${BASE_PIP_URL:-"https://pypi.python.org/simple"}
VIRTUALENV_VERSION="15.1.0"
VIRTUALENV_URL="https://raw.github.com/pypa/virtualenv/$VIRTUALENV_VERSION/virtualenv.py"

RALLY_GIT_URL="https://git.openstack.org/openstack/rally"
RALLY_GIT_BRANCH="master"
RALLY_CONFIGURATION_DIR=/etc/rally
RALLY_DATABASE_DIR=/var/lib/rally/database
DBTYPE=sqlite
DBNAME=rally.sqlite

# Variable used by script_interrupted to know what to cleanup
CURRENT_ACTION="none"

## Exit status codes (mostly following <sysexits.h>)
# successful exit
EX_OK=0

# wrong command-line invocation
EX_USAGE=64

# missing dependencies (e.g., no C compiler)
EX_UNAVAILABLE=69

# wrong python version
EX_SOFTWARE=70

# cannot create directory or file
EX_CANTCREAT=73

# user aborted operations
EX_TEMPFAIL=75

# misused as: unexpected error in some script we call
EX_PROTOCOL=76

# abort RC [MSG]
#
# Print error message MSG and abort shell execution with exit code RC.
# If MSG is not given, read it from STDIN.
#
abort () {
  local rc="$1"
  shift
  (echo -en "$RED$PROG: ERROR: $NO_COLOR";
      if [ $# -gt 0 ]; then echo "$@"; else cat; fi) 1>&2
  exit "$rc"
}

# die RC HEADER <<...
#
# Print an error message with the given header, then abort shell
# execution with exit code RC.  Additional text for the error message
# *must* be passed on STDIN.
#
die () {
  local rc="$1"
  header="$2"
  shift 2
  cat 1>&2 <<__EOF__
$RED==========================================================
$PROG: ERROR: $header
==========================================================
$NO_COLOR
__EOF__
  if [ $# -gt 0 ]; then
      # print remaining arguments one per line
      for line in "$@"; do
          echo "$line" 1>&2;
      done
  else
      # additional message text provided on STDIN
      cat 1>&2;
  fi
  cat 1>&2 <<__EOF__

If the above does not help you resolve the issue, please contact the
Rally team by sending an email to the OpenStack mailing list
openstack-dev@lists.openstack.org. Include the full output of this
script to help us identifying the problem.
$RED
Aborting installation!$NO_COLOR
__EOF__
  exit "$rc"
}

script_interrupted () {
    echo "Interrupted by the user. Cleaning up..."
    [ -n "${VIRTUAL_ENV}" -a "${VIRTUAL_ENV}" == "$VENVDIR" ] && deactivate

    case $CURRENT_ACTION in
        creating_venv|venv-created)
            if [ -d "$VENVDIR" ]
            then
                if ask_yn "Do you want to delete the virtual environment in '$VENVDIR'?"
                then
                    rm -rf "$VENVDIR"
                fi
            fi
            ;;
        downloading-src|src-downloaded)
            # This is only relevant when installing with --system,
            # otherwise the git repository is cloned into the
            # virtualenv directory
            if [ -d "$SOURCEDIR" ]
            then
                if ask_yn "Do you want to delete the downloaded source in '$SOURCEDIR'?"
                then
                    rm -rf "$SOURCEDIR"
                fi
            fi
            ;;
    esac

    abort $EX_TEMPFAIL "Script interrupted by the user"
}

trap script_interrupted SIGINT

print_usage () {
    cat <<__EOF__
Usage: $PROG [options]

This script will install Rally in your system.

Options:
$GREEN  -h, --help            $NO_COLOR Print this help text
$GREEN  -v, --verbose         $NO_COLOR Verbose mode
$GREEN  -s, --system          $NO_COLOR Install system-wide.
$GREEN  -d, --target DIRECTORY$NO_COLOR Install Rally virtual environment into DIRECTORY.
                         (Default: $HOME/rally if not root).
$GREEN  --url                 $NO_COLOR Git repository public URL to download Rally from.
                         This is useful when you have only installation script and want to install Rally
                         from custom repository.
                         (Default: ${RALLY_GIT_URL}).
                         (Ignored when you are already in git repository).
$GREEN  --branch              $NO_COLOR Git branch name, tag (Rally release), commit hash, ref, or other
                         tree-ish to install. (Default: master)
                         Ignored when you are already in git repository.
$GREEN  -f, --overwrite       $NO_COLOR Deprecated. Use -r instead.
$GREEN  -r, --recreate        $NO_COLOR Remove target directory if it already exist.
                         If neither '-r' nor '-R' is set default behaviour is to ask.
$GREEN  -R, --no-recreate     $NO_COLOR Do not remove target directory if it already exist.
                         If neither '-r' nor '-R' is set default behaviour is to ask.
$GREEN  -y, --yes             $NO_COLOR Do not ask for confirmation: assume a 'yes' reply
                         to every question.
$GREEN  -D, --dbtype TYPE     $NO_COLOR Select the database type. TYPE can be one of
                         'sqlite', 'mysql', 'postgres'.
                         Default: sqlite
$GREEN  --db-user USER        $NO_COLOR Database user to use. Only used when --dbtype
                         is either 'mysql' or 'postgres'.
$GREEN  --db-password PASSWORD$NO_COLOR Password of the database user. Only used when
                         --dbtype is either 'mysql' or 'postgres'.
$GREEN  --db-host HOST        $NO_COLOR Database host. Only used when --dbtype is
                         either 'mysql' or 'postgres'
$GREEN  --db-name NAME        $NO_COLOR Name of the database. Only used when --dbtype is
                         either 'mysql' or 'postgres'
$GREEN  -p, --python EXE      $NO_COLOR The python interpreter to use. Default: $PYTHON
$GREEN  --develop             $NO_COLOR Install Rally with editable source code try.
                         (Default: false)
$GREEN  --no-color            $NO_COLOR Disable output coloring.

__EOF__
}

# ask_yn PROMPT
#
# Ask a Yes/no question preceded by PROMPT.
# Set the env. variable REPLY to 'yes' or 'no'
# and return 0 or 1 depending on the users'
# answer.
#
ask_yn () {
    if [ $ASKCONFIRMATION -eq 0 ]; then
        # assume 'yes'
        REPLY='yes'
        return 0
    fi
    while true; do
        read -p "$1 [yN] " REPLY
        case "$REPLY" in
            [Yy]*)    REPLY='yes'; return 0 ;;
            [Nn]*|'') REPLY='no';  return 1 ;;
            *)        echo "Please type 'y' (yes) or 'n' (no)." ;;
        esac
    done
}

have_command () {
  type "$1" >/dev/null 2>/dev/null
}

require_command () {
  if ! have_command "$1"; then
    abort 1 "Could not find required command '$1' in system PATH. Aborting."
  fi
}

require_python () {
    require_command "$PYTHON"
    if "$PYTHON" -c 'import sys; sys.exit(sys.version_info[:2] >= (2, 6))'
    then
        die $EX_UNAVAILABLE "Wrong version of python is installed" <<__EOF__

Rally requires Python version 2.6+. Unfortunately, we do not support
your version of python: $("$PYTHON" -V 2>&1 | sed 's/python//gi').

If a version of Python suitable for using Rally is present in some
non-standard location, you can specify it from the command line by
running this script again with option '--python' followed by the path of
the correct 'python' binary.
__EOF__
    fi
}

which_missing_packages () {
    if [ ! -f bindep.txt ]; then
        abort $EX_PROTOCOL \
            "bindep.txt not found. Unable to find missing packages."
    fi
    require_command "bindep"
    require_command "lsb_release"
    echo "$(bindep -b | tr '\n' ' ')"
}

which_missing_commands () {
    # These commands are required to run install_rally.sh
    local missing=""
    if ! have_command "wget"; then
        missing="wget"
    fi
    if ! have_command "git"; then
        missing="$missing git"
    fi
    if ! have_command "pip"; then
        missing="$missing python-pip"
    fi
    echo "$missing"
}


# Download command
download() {
    wget -nv $VERBOSE --no-check-certificate -O "$@";
}

get_pkg_manager () {
    if have_command apt-get; then
        # Debian/Ubuntu
        if [ "$ASKCONFIRMATION" -eq 0 ]; then
            pkg_manager="apt-get install --yes"
        else
            pkg_manager="apt-get install"
        fi
    elif have_command dnf; then
        # dnf based RHEL/CentOS/Fedora
        if [ "$ASKCONFIRMATION" -eq 0 ]; then
            pkg_manager="dnf install -y"
        else
            pkg_manager="dnf install"
        fi
    elif have_command yum; then
        # yum based RHEL/CentOS/Fedora
        if [ "$ASKCONFIRMATION" -eq 0 ]; then
            pkg_manager="yum install -y"
        else
            pkg_manager="yum install"
        fi
    elif have_command zypper; then
        # SuSE
        if [ "$ASKCONFIRMATION" -eq 0 ]; then
            pkg_manager="zypper -n --no-gpg-checks --non-interactive install --auto-agree-with-licenses"
        else
            pkg_manager="zypper install"
        fi
    else
        # MacOSX maybe?
        echo "Cannot determine what package manager this system has, so I cannot check if requisite software is installed. I'm proceeding anyway, but you may run into errors later."
    fi
    echo $pkg_manager
}

install_required_sw () {
    # instead of guessing which distribution this is, we check for the
    # package manager name as it basically identifies the distro
    local missing pkg_manager
    missing=$1
    pkg_manager=$(get_pkg_manager)

    if [ -n "$missing" ]; then
        cat <<__EOF__
The following software packages need to be installed
in order for Rally to work:$GREEN $missing
$NO_COLOR
__EOF__

        # If we are root
        if running_as_root; then
            cat <<__EOF__
In order to install the required software you would need to run as
'root' the following command:
$GREEN
    $pkg_manager $missing
$NO_COLOR
__EOF__
            # ask if we have to install it
            if ask_yn "Do you want me to install these packages for you?"; then
                # install
                if [[ "$missing" == *python-pip* ]]; then
                    missing=${missing//python-pip/}
                    if ! $pkg_manager python-pip; then
                        if ask_yn "Error installing python-pip. Install from external source?"; then
                            local pdir=$(mktemp /tmp/tmp.XXXXXXXXXX -d)
                            local getpip="$pdir/get-pip.py"
                            download "$getpip" https://bootstrap.pypa.io/get-pip.py
                            if ! "$PYTHON" "$getpip"; then
                                abort $EX_PROTOCOL "Error while installing python-pip from external source."
                            fi
                        else
                            abort $EX_TEMPFAIL \
                                "Please install python-pip manually."
                        fi
                    fi
                fi
                if [ -n "$missing" ] && ! $pkg_manager $missing; then
                    abort $EX_UNAVAILABLE "Error while installing $missing"
                fi
                # installation successful
            else # don't want to install the packages
                die $EX_UNAVAILABLE "missing software prerequisites" <<__EOF__
Please, install the required software before installing Rally

__EOF__
            fi
        else # Not running as root
            cat <<__EOF__
There is a small chance that the required software
is actually installed though we failed to detect it,
so you may choose to proceed with Rally installation
anyway.  Be warned however, that continuing is very
likely to fail!

__EOF__
            if ask_yn "Proceed with installation anyway?"
            then
                echo "Proceeding with installation at your request... keep fingers crossed!"
            else
                die $EX_UNAVAILABLE "missing software prerequisites" <<__EOF__
Please ask your system administrator to install the missing packages,
or, if you have root access, you can do that by running the following
command from the 'root' account:
$GREEN
    $pkg_manager $missing
$NO_COLOR
__EOF__
            fi
        fi
    fi

}

install_db_connector () {
    case $DBTYPE in
        mysql)
            pip install pymysql
            ;;
        postgres)
            pip install psycopg2
            ;;
    esac
}

install_virtualenv () {
    DESTDIR=$1

    if [ -n "$VIRTUAL_ENV" ]; then
        die $EX_SOFTWARE "Virtualenv already active" <<__EOF__
A virtual environment seems to be already active. This will cause
this script to FAIL.

Run 'deactivate', then run this script again.
__EOF__
    fi

    # Use the latest virtualenv that can use `.tar.gz` files
    VIRTUALENV_DST="$DESTDIR/virtualenv-$VIRTUALENV_VERSION.py"
    mkdir -p "$DESTDIR"
    download "$VIRTUALENV_DST" "$VIRTUALENV_URL"
    "$PYTHON" "$VIRTUALENV_DST" $VERBOSE --no-setuptools --no-pip --no-wheel \
        -p "$PYTHON" "$DESTDIR"

    cd "${DESTDIR}" && . bin/activate

    download - https://bootstrap.pypa.io/get-pip.py | python -\
        || die $EX_PROTOCOL \
        "Error while running get-pip.py" <<__EOF__

The required Python package pip could not be installed
in virtualenv.

__EOF__

    pip install setuptools wheel || die $EX_PROTOCOL \
        "Error while running 'pip install setuptools wheel'" <<__EOF__

The required Python package setuptools, wheel could not be installed
in virtualenv.

__EOF__
}

setup_rally_configuration () {
    SRCDIR=$1
    ETCDIR=$RALLY_CONFIGURATION_DIR
    DBDIR=$RALLY_DATABASE_DIR

    [ -d "$ETCDIR" ] || mkdir -p "$ETCDIR"
    cp "$SRCDIR"/etc/rally/rally.conf.sample "$ETCDIR"/rally.conf

    [ -d "$DBDIR" ] || mkdir -p "$DBDIR"
    local CONF_TMPFILE=$(mktemp /tmp/tmp.XXXXXXXXXX)
    sed "s|#connection *=.*|connection = \"$DBCONNSTRING\"|" "$ETCDIR"/rally.conf > "$CONF_TMPFILE"
    cat "$CONF_TMPFILE" > "$ETCDIR"/rally.conf
    rm "$CONF_TMPFILE"
    rally-manage db recreate
}

rally_venv () {
    echo "Installing Rally virtualenv in directory '$VENVDIR' ..."
    CURRENT_ACTION="creating-venv"
    if ! install_virtualenv "$VENVDIR"; then
        die $EX_PROTOCOL "Unable to create a new virtualenv in '$VENVDIR': 'virtualenv.py' script exited with code $rc." <<__EOF__
The script was unable to create a valid virtual environment.
__EOF__
    fi
    CURRENT_ACTION="venv-created"
    rc=0
}

### Main program ###
short_opts='d:vsyfrRhD:p:'
long_opts='target:,verbose,overwrite,recreate,no-recreate,system,yes,dbtype:,python:,db-user:,db-password:,db-host:,db-name:,help,url:,branch:,develop,no-color'

set +e
if [ "x$(getopt -T)" = 'x' ]; then
    # GNU getopt
    args=$(getopt --name "$PROG" --shell sh -l "$long_opts" -o "$short_opts" -- "$@")
    if [ $? -ne 0 ]; then
        abort 1 "Type '$PROG --help' to get usage information."
    fi
    # use 'eval' to remove getopt quoting
    eval set -- "$args"
else
    # old-style getopt, use compatibility syntax
    args=$(getopt "$short_opts" "$@")
    if [ $? -ne 0 ]; then
        abort 1 "Type '$PROG -h' to get usage information."
    fi
    eval set -- "$args"
fi
set -e

# Command line parsing
while true
do
    case "$1" in
        -d|--target)
            shift
            VENVDIR=$(readlink -m "$1")
            ;;
        -h|--help)
            print_usage
            exit $EX_OK
            ;;
        -v|--verbose)
            VERBOSE="-v"
            ;;
        -s|--system)
            USEVIRTUALENV="no"
            ;;
        -f|--overwrite)
            RECREATEDEST=yes
            ;;
        -r|--recreate)
            RECREATEDEST=yes
            ;;
        -R|--no-recreate)
            RECREATEDEST=no
            ;;
        -y|--yes)
            ASKCONFIRMATION=0
            ;;
        --url)
            shift
            RALLY_GIT_URL=$1
            ;;
        --branch)
            shift
            RALLY_GIT_BRANCH=$1
            ;;
        -D|--dbtype)
            shift
            DBTYPE=$1
            case $DBTYPE in
                sqlite|mysql|postgres);;
                *)
                    print_usage | die $EX_USAGE \
                        "An invalid option has been detected."
                    ;;
            esac
            ;;
        --db-user)
            shift
            DBUSER=$1
            ;;
        --db-password)
            shift
            DBPASSWORD=$1
            ;;
        --db-host)
            shift
            DBHOST=$1
            ;;
        --db-name)
            shift
            DBNAME=$1
            ;;
        -p|--python)
            shift
            PYTHON=$1
            ;;
        --develop)
            DEVELOPMENT_MODE=true
            ;;
        --no-color)
            RED=""
            GREEN=""
            NO_COLOR=""
            ;;
        --)
            shift
            break
            ;;
        *)
            print_usage | die $EX_USAGE "An invalid option has been detected."
    esac
    shift
done

### Post-processing ###

if [ "$USEVIRTUALENV" == "no" ] && [ -n "$VENVDIR" ]; then
    die $EX_USAGE "Ambiguous arguments" <<__EOF__
Option -d/--target can not be used with --system.
__EOF__
fi

if running_as_root; then
    if [ -z "$VENVDIR" ]; then
        USEVIRTUALENV='no'
    fi
else
    if [ "$USEVIRTUALENV" == 'no' ]; then
        die $EX_USAGE "Insufficient privileges" <<__EOF__
$REDRoot permissions required in order to install system-wide.
As non-root user you may only install in virtualenv.$NO_COLOR
__EOF__
    fi
    if [ -z "$VENVDIR" ]; then
        VENVDIR="$HOME"/rally
    fi
fi

# Fix RALLY_DATABASE_DIR if virtualenv is used
if [ "$USEVIRTUALENV" = 'yes' ]
then
    RALLY_CONFIGURATION_DIR=$VENVDIR/etc/rally
    RALLY_DATABASE_DIR="$VENVDIR"/database
fi

if [ "$DBTYPE" = 'sqlite' ]; then
    if [ "${DBNAME:0:1}" = '/' ]; then
        DBFILE="$DBNAME"
    else
        DBFILE="${RALLY_DATABASE_DIR}/${DBNAME}"
    fi
    DBCONNSTRING="sqlite:///${DBFILE}"
else
    if [ -z "$DBUSER" -o -z "$DBPASSWORD" -o -z "$DBHOST" -o -z "$DBNAME" ]
    then
        die $EX_USAGE "Missing mandatory options" <<__EOF__
When specifying a database type different than 'sqlite', you also have
to specify the database name, host, and username and password of a
valid user with write access to the database.

Please, re-run the script with valid values for the options:
$GREEN
    --db-host
    --db-name
    --db-user
    --db-password$NO_COLOR
__EOF__
    fi
    DBAUTH="$DBUSER:$DBPASSWORD@$DBHOST"
    if [ "$DBTYPE" = 'mysql' ]; then
        DBCONNSTRING="$DBTYPE+pymysql://$DBAUTH/$DBNAME"
    else
        DBCONNSTRING="$DBTYPE://$DBAUTH/$DBNAME"
    fi
fi

# check and install prerequisites
install_required_sw "$(which_missing_commands)"
require_python


# Install virtualenv, if required
if [ "$USEVIRTUALENV" = 'yes' ]; then
    if [ -d "$VENVDIR" ]
    then
        if [ $RECREATEDEST = 'ask' ]; then
            echo "Destination directory '$VENVDIR' already exists."
            echo "I can wipe it out in order to make a new installation,"
            echo "but this means any files in that directory, and the ones"
            echo "underneath it will be deleted."
            echo

            if ! ask_yn "Do you want to wipe the installation directory '$VENVDIR'?"
            then
                echo "*Not* overwriting destination directory '$VENVDIR'."
                RECREATEDEST=no
            else
                RECREATEDEST=yes

            fi
        fi

        if [ $RECREATEDEST = 'yes' ];
        then
            echo "Removing directory $VENVDIR as requested."
            rm $VERBOSE -rf "$VENVDIR"
            rally_venv
        elif [ $RECREATEDEST = 'no' ];
        then
            echo "Using existing virtualenv at $VENVDIR..."
            . "$VENVDIR"/bin/activate
        else
            abort 66 "Internal error: unexpected value '$RECREATEDEST' for RECREATEDEST."
        fi
    else
        rally_venv
    fi
fi

# Install rally
ORIG_WD=$(pwd)

BASEDIR=$(dirname "$(readlink -e "$0")")

# If we are inside the git repo, don't download it again.
if [ -d "$BASEDIR"/.git ]
then
    SOURCEDIR=$BASEDIR
    (
        cd "$BASEDIR"
        if find . -name '*.py[co]' -exec rm -f {} +; then
            echo "Wiped python compiled files."
        else
            echo "Warning! Unable to wipe python compiled files"
        fi
    )
else
    if [ "$USEVIRTUALENV" = 'yes' ]
    then
        SOURCEDIR="$VENVDIR"/src
    else
        SOURCEDIR="$ORIG_WD"/rally.git
    fi

    if ! [ -d "$SOURCEDIR"/.git ]
    then
        echo "Downloading Rally from git repository $RALLY_GIT_URL ..."
        CURRENT_ACTION="downloading-src"
        git clone "$RALLY_GIT_URL" "$SOURCEDIR"
        (
            cd "$SOURCEDIR"
            git checkout "$RALLY_GIT_BRANCH"
        )
        if ! [ -d "$SOURCEDIR"/.git ]; then
            abort $EX_CANTCREAT "Unable to download git repository"
        fi
        CURRENT_ACTION="src-downloaded"
    fi
fi

install_db_connector

# Install rally
cd "$SOURCEDIR"
# Get latest available pip and reset shell cache
pip install -i "$BASE_PIP_URL" -U 'pip!=8'
hash -r

# Install dependencies
pip install -i "$BASE_PIP_URL" pbr 'tox<=1.6.1' bindep

# Install binary dependencies
install_required_sw "$(which_missing_packages)"

# Uninstall possible previous version
pip uninstall -y rally || true
# Install rally
if [ "$DEVELOPMENT_MODE" = "true" ]; then
    pip install -i "$BASE_PIP_URL" -e .
else
    pip install -i "$BASE_PIP_URL" .
fi

cd "$ORIG_WD"

# Post-installation
if [ "$USEVIRTUALENV" = 'yes' ]
then
    # Fix bash_completion
    cat >> "$VENVDIR"/bin/activate <<__EOF__

. "$VENVDIR/etc/bash_completion.d/rally.bash_completion"
__EOF__

    setup_rally_configuration "$SOURCEDIR"

    if ! [ "$DEVELOPMENT_MODE" = "true" ]; then
        SAMPLESDIR=$VENVDIR/samples
        mkdir -p "$SAMPLESDIR"
        cp -r "$SOURCEDIR"/samples/* "$SAMPLESDIR"/
    fi
    mkdir -p "$VENVDIR"/etc/bash_completion.d
    install "$SOURCEDIR"/etc/rally.bash_completion \
        "$VENVDIR"/etc/bash_completion.d/

    cat <<__EOF__
$GREEN==============================
Installation of Rally is done!
==============================
$NO_COLOR
In order to work with Rally you have to enable the virtual environment
with the command:

    . $VENVDIR/bin/activate

You need to run the above command on every new shell you open before
using Rally, but just once per session.

Information about your Rally installation:

  * Method:$GREEN virtualenv$NO_COLOR
  * Virtual Environment at:$GREEN $VENVDIR$NO_COLOR
  * Database at:$GREEN $RALLY_DATABASE_DIR$NO_COLOR
  * Configuration file at:$GREEN $RALLY_CONFIGURATION_DIR$NO_COLOR
  * Samples at:$GREEN $SAMPLESDIR$NO_COLOR

__EOF__
else
    setup_rally_configuration "$SOURCEDIR"

    if ! [ "$DEVELOPMENT_MODE" = "true" ]; then
        SAMPLESDIR=/usr/share/rally/samples
        mkdir -p "$SAMPLESDIR"
        cp -r "$SOURCEDIR"/samples/* "$SAMPLESDIR"/
    fi
    ln -s /usr/local/etc/bash_completion.d/rally.bash_completion \
        /etc/bash_completion.d/ 2> /dev/null || true
    if [ -f "${DBFILE}" ]; then
        chmod 777 "$DBFILE"
    fi

    cat <<__EOF__
$GREEN==============================
Installation of Rally is done!
==============================
$NO_COLOR
Rally is now installed in your system. Information about your Rally
installation:

  * Method:$GREEN system$NO_COLOR
  * Database at:$GREEN $RALLY_DATABASE_DIR$NO_COLOR
  * Configuration file at:$GREEN $RALLY_CONFIGURATION_DIR$NO_COLOR
  * Samples at:$GREEN $SAMPLESDIR$NO_COLOR
__EOF__
fi
