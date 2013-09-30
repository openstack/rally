DATABASE_PASSWORD=b63a9cca3cd359cc32ed
RABBIT_PASSWORD=a9fd294d3977ec2eb41e
SERVICE_TOKEN=95f65562216379062794
SERVICE_PASSWORD=c2ec0d6c0aae31959ead
ADMIN_PASSWORD={{ admin_password }}

RECLONE=yes
SYSLOG=True

#Nova configuration
{% if nova %}
NOVA_REPO={{ nova.repo }}
NOVA_BRANCH={{ nova.branch }}
{% endif %}
