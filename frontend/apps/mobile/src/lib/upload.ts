/**
 * Ish hujjatlarini tanlash (designs/tezkor_skaner_batch): kamera (ketma-ket suratlar), galereya (ko'p rasm),
 * fayllar (PDF/DOCX/JPG/PNG). Server ularni bitta PDF ga birlashtiradi (apps/cases/intake.py), rasmlarni OCR qiladi.
 * expo/fetch FormData da `{uri}` qismlarini qo'llamaydi — fayl `expo-file-system` `File` (Blob) sifatida qo'shiladi.
 */
import type { Schemas } from "@mezon/api-client";
import * as DocumentPicker from "expo-document-picker";
import { File } from "expo-file-system";
import * as ImagePicker from "expo-image-picker";
import { Platform } from "react-native";

import { authedFetch } from "./api";

export interface PickedFile {
  uri: string;
  name: string;
  mimeType: string;
  size?: number;
}

const stamp = () => new Date().toISOString().replace(/[-:T]/g, "").slice(0, 14);

function fromAsset(a: ImagePicker.ImagePickerAsset, i: number): PickedFile {
  const mime = a.mimeType ?? "image/jpeg";
  const ext = mime.includes("png") ? "png" : "jpg";
  return { uri: a.uri, name: a.fileName ?? `skan_${stamp()}_${i + 1}.${ext}`, mimeType: mime, size: a.fileSize };
}

/** Kamera: bitta surat (skaner rejimida ekran qayta-qayta chaqiradi). null — bekor qilindi yoki ruxsat yo'q. */
export async function takePhoto(): Promise<PickedFile | null | "denied"> {
  const perm = await ImagePicker.requestCameraPermissionsAsync();
  if (!perm.granted) return "denied";
  const res = await ImagePicker.launchCameraAsync({ mediaTypes: ["images"], quality: 0.85, exif: false });
  return res.canceled ? null : fromAsset(res.assets[0], 0);
}

export async function pickImages(): Promise<PickedFile[]> {
  const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ["images"], allowsMultipleSelection: true, quality: 0.85,
    selectionLimit: 20, exif: false });
  return res.canceled ? [] : res.assets.map(fromAsset);
}

export async function pickDocuments(): Promise<PickedFile[]> {
  const res = await DocumentPicker.getDocumentAsync({
    multiple: true,
    copyToCacheDirectory: true,
    type: ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "image/jpeg", "image/png"],
  });
  return res.canceled ? [] : res.assets.map((a) => ({ uri: a.uri, name: a.name, mimeType: a.mimeType ?? "application/octet-stream", size: a.size }));
}

async function asBlob(f: PickedFile): Promise<Blob> {
  if (Platform.OS === "web") return (await fetch(f.uri)).blob();
  return new File(f.uri);
}

export async function uploadCase(files: PickedFile[], fields: { title: string; category: string; zeroRetention: boolean }) {
  const form = new FormData();
  for (const f of files) form.append("files", await asBlob(f), f.name);
  form.append("category", fields.category);
  form.append("title", fields.title);
  if (fields.zeroRetention) form.append("zero_retention", "true");
  return (await (await authedFetch("/cases/", { method: "POST", body: form })).json()) as Schemas["CaseDetail"];
}
