FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app
COPY pom.xml .
COPY src/ src/

RUN apk add --no-cache maven && mvn package -DskipTests -q

FROM eclipse-temurin:21-jre-alpine

WORKDIR /app
COPY --from=builder /app/target/*.jar app.jar

EXPOSE 8081
CMD ["java", "-jar", "app.jar"]
