apiVersion: v1
kind: Secret
metadata:
  name: mysql-secret
  namespace: mkc-dev
  labels:
    app.kubernetes.io/part-of: mkc
type: Opaque
stringData:
  root-password: "${MYSQL_ROOT_PASSWORD}"
  password: "${MYSQL_PASSWORD}"
# NOTE: This file is generated from secret.yaml.tpl by render-secrets.sh.
# Do NOT commit the rendered secret.yaml to Git.
