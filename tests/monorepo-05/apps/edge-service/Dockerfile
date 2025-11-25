FROM openjdk:11-jre-slim

WORKDIR /app
COPY target/edge-service.jar app.jar

EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
