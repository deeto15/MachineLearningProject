package auth

import (
	"net/http"
	"slices"
	"time"

	"github.com/golang-jwt/jwt/v5"
)

type WSUserClaims struct {
	UserID        string `json:"user_id"`
	AllowedTopics []string
	jwt.RegisteredClaims
}

func GenerateJWT(secret string, userID string, allowedTopics []string, expiresIn time.Duration) (string, error) {
	claims := WSUserClaims{
		UserID:        userID,
		AllowedTopics: allowedTopics,
		RegisteredClaims: jwt.RegisteredClaims{
			ExpiresAt: jwt.NewNumericDate(time.Now().Add(expiresIn)),
			IssuedAt:  jwt.NewNumericDate(time.Now()),
			Issuer:    "live-updater",
		},
	}

	token := jwt.NewWithClaims(jwt.SigningMethodHS256, claims)

	return token.SignedString([]byte(secret))
}

func (w *WSUserClaims) HasTopic(topic string) bool {
	return slices.Contains(w.AllowedTopics, topic)
}

func GetClaims(r *http.Request) *WSUserClaims {
	claims, ok := r.Context().Value(UserClaimsKey).(*WSUserClaims)
	if !ok || claims == nil {
		return nil
	}

	return claims
}
