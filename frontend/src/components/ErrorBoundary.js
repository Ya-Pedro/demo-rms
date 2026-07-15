import React from 'react';
import { Result, Button, Typography } from 'antd';
import { ReloadOutlined, BugOutlined } from '@ant-design/icons';

const { Paragraph, Text } = Typography;

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true };
  }

  componentDidCatch(error, errorInfo) {
    this.setState({
      error: error,
      errorInfo: errorInfo
    });
    console.error("ErrorBoundary caught an error:", error, errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'flex-start', paddingTop: '10vh', background: '#f8fafc', paddingBottom: '20px', paddingLeft: '20px', paddingRight: '20px' }}>
          <Result
            status="500"
            title="Ой, что-то пошло не так!"
            subTitle="Произошла непредвиденная ошибка в приложении. Пожалуйста, передайте детали ошибки разработчику."
            extra={[
              <Button type="primary" key="console" onClick={this.handleReload} icon={<ReloadOutlined />}>
                Обновить страницу
              </Button>
            ]}
          >
            <div className="desc" style={{ background: '#fff', padding: '24px', borderRadius: '12px', border: '1px solid #e2e8f0', textAlign: 'left', maxWidth: '800px', margin: '0 auto', overflow: 'auto', maxHeight: '50vh', boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.05)' }}>
              <Paragraph>
                <Text strong style={{ fontSize: 16 }}>
                  <BugOutlined style={{ color: '#ef4444', marginRight: 8 }} />
                  Техническая информация об ошибке:
                </Text>
              </Paragraph>
              <Paragraph style={{ marginBottom: 8 }}>
                <Text type="danger" strong>{this.state.error && this.state.error.toString()}</Text>
              </Paragraph>
              {this.state.errorInfo && (
                <pre style={{ fontSize: 13, color: '#64748b', whiteSpace: 'pre-wrap', background: '#f1f5f9', padding: '12px', borderRadius: '6px' }}>
                  {this.state.errorInfo.componentStack}
                </pre>
              )}
            </div>
          </Result>
        </div>
      );
    }

    return this.props.children; 
  }
}

export default ErrorBoundary;