use axum::{
    extract::{
        ws::{Message, WebSocket, WebSocketUpgrade},
        State,
    },
    response::Response,
};
use chrono::Utc;
use futures::{sink::SinkExt, stream::StreamExt};
use tokio::sync::broadcast;
use tracing::{error, info};

use crate::{models::WebSocketMessage, AppState};

pub async fn websocket_handler(
    ws: WebSocketUpgrade,
    State(state): State<AppState>,
) -> Response {
    ws.on_upgrade(|socket| handle_socket(socket, state))
}

async fn handle_socket(socket: WebSocket, state: AppState) {
    let (mut sender, mut receiver) = socket.split();
    
    // Subscribe to automation updates
    let mut automation_rx = state.automation_tx.subscribe();
    
    // Send connection acknowledgment
    let ack_message = WebSocketMessage::ConnectionAck {
        timestamp: Utc::now(),
        message: "Connected to FormAI Rust automation server".to_string(),
        server_version: "1.0.0".to_string(),
    };
    
    if let Ok(message_json) = serde_json::to_string(&ack_message) {
        if let Err(e) = sender.send(Message::Text(message_json.into())).await {
            error!("Failed to send connection ack: {}", e);
            return;
        }
        info!("WebSocket connection established");
    }
    
    // Handle WebSocket messages
    loop {
        tokio::select! {
            // Handle incoming messages from client
            msg = receiver.next() => {
                match msg {
                    Some(Ok(Message::Text(text))) => {
                        info!("Received WebSocket message: {}", text);
                        // Handle client messages if needed
                    }
                    Some(Ok(Message::Close(_))) => {
                        info!("WebSocket connection closed by client");
                        break;
                    }
                    Some(Ok(Message::Ping(data))) => {
                        if let Err(e) = sender.send(Message::Pong(data)).await {
                            error!("Failed to send pong: {}", e);
                            break;
                        }
                        info!("WebSocket ping-pong handled");
                    }
                    Some(Ok(Message::Pong(_))) => {
                        info!("WebSocket pong received");
                    }
                    Some(Ok(_)) => {
                        // Handle other message types if needed
                    }
                    Some(Err(e)) => {
                        error!("WebSocket error: {}", e);
                        break;
                    }
                    None => {
                        info!("WebSocket stream ended");
                        break;
                    }
                }
            }
            
            // Handle automation updates
            Ok(automation_msg) = automation_rx.recv() => {
                if let Ok(message_json) = serde_json::to_string(&automation_msg) {
                    if let Err(e) = sender.send(Message::Text(message_json.into())).await {
                        error!("Failed to send automation update: {}", e);
                        break;
                    }
                } else {
                    error!("Failed to serialize automation message");
                }
            }
        }
    }
    
    info!("WebSocket connection closed");
}

pub async fn broadcast_automation_message(
    state: &AppState,
    message: WebSocketMessage,
) -> Result<(), broadcast::error::SendError<WebSocketMessage>> {
    let receiver_count = state.automation_tx.receiver_count();
    
    // Always log the message type for debugging
    match &message {
        WebSocketMessage::ScriptLog { message: msg, .. } => {
            info!("📨 Broadcasting ScriptLog: {}", msg);
        },
        WebSocketMessage::AutomationStarted { message: msg, .. } => {
            info!("📨 Broadcasting AutomationStarted: {}", msg);
        },
        WebSocketMessage::AutomationCompleted { message: msg, .. } => {
            info!("📨 Broadcasting AutomationCompleted: {}", msg);
        },
        WebSocketMessage::AutomationProgress { message: msg, .. } => {
            info!("📨 Broadcasting AutomationProgress: {}", msg);
        },
        WebSocketMessage::RecordingStarted { message: msg, .. } => {
            info!("📨 Broadcasting RecordingStarted: {}", msg);
        },
        WebSocketMessage::RecordingAction { message: msg, .. } => {
            info!("📨 Broadcasting RecordingAction: {}", msg);
        },
        WebSocketMessage::RecordingCompleted { message: msg, .. } => {
            info!("📨 Broadcasting RecordingCompleted: {}", msg);
        },
        WebSocketMessage::AIFillStarted { message: msg, .. } => {
            info!("📨 Broadcasting AIFillStarted: {}", msg);
        },
        WebSocketMessage::AIFillProgress { message: msg, .. } => {
            info!("📨 Broadcasting AIFillProgress: {}", msg);
        },
        WebSocketMessage::AIFillCompleted { message: msg, .. } => {
            info!("📨 Broadcasting AIFillCompleted: {}", msg);
        },
        _ => {
            info!("📨 Broadcasting message type: {:?}", std::mem::discriminant(&message));
        }
    }
    
    if receiver_count == 0 {
        info!("⚠️ No WebSocket clients connected (receiver_count = 0)");
        return Ok(());
    }
    
    info!("✅ Sending to {} WebSocket client(s)", receiver_count);
    match state.automation_tx.send(message) {
        Ok(receiver_count) => {
            info!("✅ Message sent to {} receivers", receiver_count);
            Ok(())
        },
        Err(e) => {
            error!("❌ Failed to send message: {}", e);
            Err(e)
        }
    }
}