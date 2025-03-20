# ITBench: SRE Sample Applications

## [OpenTelemetry's Astronomy Shop](https://github.com/open-telemetry/opentelemetry-demo)

OpenTelemetry's Astronomy Shop is a microservice-based distributed system intended to illustrate the implementation of OpenTelemetry in a near real-world environment.
An architectural diagram for the same can be found [here](https://opentelemetry.io/docs/demo/architecture/).

### Installing OpenTelemetry's Astronomy Shop
To install the application run:
```bash
make deploy_astronomy_shop
```

### Uninstalling OpenTelemetry's Astronomy Shop
To uninstall the application run:
```bash
make undeploy_astronomy_shop
```

## [Deathstarbench's HotelReservation](https://github.com/delimitrou/DeathStarBench/tree/master/hotelReservation)
A hotel reservation service built with Go and gPRC. Additional information can be found [here](https://github.com/delimitrou/DeathStarBench/tree/master/hotelReservation).

For our setup, we leverage a forked version of Deathstarbench's HotelReservation with OpenTelemetry Collector setup. That can be found [here](https://github.com/it-bench/DeathStarBench).

### Installing Deathstarbench's HotelReservation
To install the application run:
```bash
make deploy_hotel_reservation
```

### Uninstalling Deathstarbench's HotelReservation
To uninstall the application run:
```bash
make undeploy_hotel_reservation
```

## [Elastic's Elasticsearch](https://github.com/elastic/elasticsearch)

### Installing Elastic's Elasticsearch
To install the application run:
```bash
make deploy_elasticsearch
```

### Uninstalling Elastic's Elasticsearch
To uninstall the application run:
```bash
make undeploy_elasticsearch
```