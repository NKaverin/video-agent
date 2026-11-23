import { PipecatClient, RTVIEvent } from "@pipecat-ai/client-js";
import { SmallWebRTCTransport } from "@pipecat-ai/small-webrtc-transport";
import "./style.css";

function element<T extends HTMLElement>(selector: string): T {
  const found = document.querySelector<T>(selector);
  if (!found) {
    throw new Error("Missing element " + selector);
  }
  return found;
}

const connectButton = element<HTMLButtonElement>("#connect");
const statusText = element<HTMLSpanElement>("#status");
const botAudio = element<HTMLAudioElement>("#bot-audio");
const transcript = element<HTMLOListElement>("#transcript");

function addLine(speaker: string, text: string): void {
  const line = document.createElement("li");
  line.textContent = speaker + ": " + text;
  transcript.append(line);
  line.scrollIntoView({ block: "nearest" });
}

const client = new PipecatClient({
  transport: new SmallWebRTCTransport(),
  enableMic: true,
  enableCam: false,
});

client.on(RTVIEvent.TransportStateChanged, (state) => {
  statusText.textContent = state;
});

client.on(RTVIEvent.TrackStarted, (track, participant) => {
  if (track.kind === "audio" && !participant?.local) {
    botAudio.srcObject = new MediaStream([track]);
  }
});

client.on(RTVIEvent.UserInput, (data) => {
  if (data.final) {
    addLine("You", data.text);
  }
});

client.on(RTVIEvent.BotOutput, (data) => {
  if (data.spoken_status === "completed") {
    addLine("Bot", data.text);
  }
});

client.on(RTVIEvent.Disconnected, () => {
  connectButton.textContent = "Connect";
});

async function toggleConnection(): Promise<void> {
  connectButton.disabled = true;
  try {
    if (client.connected) {
      await client.disconnect();
    } else {
      await client.connect({ webrtcRequestParams: { endpoint: "/api/offer" } });
      connectButton.textContent = "Disconnect";
    }
  } catch (error) {
    console.error("connection failed", error);
  } finally {
    connectButton.disabled = false;
  }
}

connectButton.addEventListener("click", toggleConnection);
