# k8s-mongo-db-provider
This project helps with auto-provisioning of MongoDb databases within Kubernetes. It provides a Custom Resource Definition, helping you to achieve isolation within your microservice environment (aka. database per microservice)

Works out of the box with MongoDb Replicaset helm chart (https://github.com/helm/charts/tree/master/stable/mongodb-replicaset)

## Quickstart
First, you need to install CRD (Custom resource definition) within your cluster:
```bash
kubectl apply -f https://raw.githubusercontent.com/onliner10/k8s-mongo-db-provider/master/crd.yaml
```

This will allow you to create resources of kind `MongoDatabase` and things like `kubectl get mongodb` etc..

Then, we need a controller (review this file before doing deployment to production):
```bash
kubectl apply -f https://raw.githubusercontent.com/onliner10/k8s-mongo-db-provider/master/examples/controller-deployment.yaml
```
That's it! If you now create a following resource:
```yaml
apiVersion: mongo-db-provider.urbanonsoftware.com/v1alpha1
kind: MongoDatabase
metadata:
  name: my-mongo-database
```
The controller will initalize `my-mongo-database`, plus create two secrets for you: `my-mongo-database-reader` and `my-mongo-database-writer`. The reader has readonly permissions, while the writer can .. well, write.

You can use these secrets like so:
```yaml
containers:
        - name: kubernetes-hello
          image: mdb_provider_test:local
          imagePullPolicy: Never
          ports:
            - containerPort: 80
          env:
            - name: ASPNETCORE_ENVIRONMENT
              value: "Development"
            - name: MongoDb__ConnectionString
              valueFrom:
                secretKeyRef:
                  name: my-mongo-database-writer
                  key: ConnectionString
            - name: MongoDb__DbName
              valueFrom:
                secretKeyRef:
                  name: my-mongo-database-writer
                  key: DbName
```

If you would like to drop the database + secrets, simply fire
```bash
kubectl delete mongodb my-mongo-database
```

## Config options

| Environmental variable | Description                                                                                                          |
|------------------------|----------------------------------------------------------------------------------------------------------------------|
| CLUSTER\_DOMAIN        | Domain of your cluster\. Defaults to `cluster.local`                                                               |
| MONGO\_APP\_NAME       | App label value used to find mongodb in your cluster\. Defaults to : `mongodb-replicaset`                          |
| TLS                    | Use TLS when connecting to mongo? Default: false                                                                     |
| HARD\_DELETE           | Drop database when CRS is deleted ? Defaults to false, meaning it will delete the secrets but not the databse itself |
