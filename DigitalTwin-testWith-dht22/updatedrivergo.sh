cd ~/dht22

cat > driver/driver.go <<'EOF'
package driver

import (
	"encoding/json"
	"fmt"
	"os/exec"
	"strings"
	"sync"

	"github.com/kubeedge/mapper-framework/pkg/common"
)

type dhtReading struct {
	Temperature float64 `json:"temperature"`
	Humidity    float64 `json:"humidity"`
}

func NewClient(protocol ProtocolConfig) (*CustomizedClient, error) {
	client := &CustomizedClient{
		ProtocolConfig: protocol,
		deviceMutex:    sync.Mutex{},
	}
	return client, nil
}

func (c *CustomizedClient) InitDevice() error {
	return nil
}

func (c *CustomizedClient) GetDeviceData(visitor *VisitorConfig) (interface{}, error) {
	c.deviceMutex.Lock()
	defer c.deviceMutex.Unlock()

	pin := strings.TrimSpace(visitor.VisitorConfigData.Pin)
	metric := strings.ToLower(strings.TrimSpace(visitor.VisitorConfigData.Metric))

	if pin == "" {
		return nil, fmt.Errorf("visitor config pin is empty")
	}
	if metric == "" {
		return nil, fmt.Errorf("visitor config metric is empty")
	}

	cmd := exec.Command(
		"python3",
		"/home/pigateway/dht22/read_dht22_once.py",
		pin,
	)

	out, err := cmd.Output()
	if err != nil {
		return nil, fmt.Errorf("failed to execute sensor reader: %v", err)
	}

	var reading dhtReading
	if err := json.Unmarshal(out, &reading); err != nil {
		return nil, fmt.Errorf("failed to parse sensor reader output: %v, output=%s", err, string(out))
	}

	switch metric {
	case "temperature":
		return fmt.Sprintf("%.1f", reading.Temperature), nil
	case "humidity":
		return fmt.Sprintf("%.1f", reading.Humidity), nil
	default:
		return nil, fmt.Errorf("unsupported metric: %s", metric)
	}
}

func (c *CustomizedClient) DeviceDataWrite(visitor *VisitorConfig, deviceMethodName string, propertyName string, data interface{}) error {
	return nil
}

func (c *CustomizedClient) SetDeviceData(data interface{}, visitor *VisitorConfig) error {
	return nil
}

func (c *CustomizedClient) StopDevice() error {
	return nil
}

func (c *CustomizedClient) GetDeviceStates() (string, error) {
	return common.DeviceStatusOK, nil
}

func (c *CustomizedClient) AnomalyDetectionProcess(req *AnomalyDetectionRequest) error {
	return nil
}
EOF