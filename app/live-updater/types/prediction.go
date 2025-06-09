package types

type Prediction struct {
	CommentID     string   `json:"comment_id"`
	Stock         string   `json:"stock"`
	Price         string   `json:"price"`
	Date          string   `json:"date"`
	FormattedDate string   `json:"formatted_date"`
	StockScore    float64  `json:"stock_score"`
	PriceScore    float64  `json:"price_score"`
	DateScore     float64  `json:"date_score"`
	NerVersion    string   `json:"ner_version"`
	BinaryModel   string   `json:"binary_model"`
	Prediction    int      `json:"prediction"`
	Confidence    float64  `json:"confidence"`
	OptionType    *string  `json:"option_type"`
	Quantity      *int     `json:"quantity"`
	Premium       *float64 `json:"premium"`
}
