/**
 * Expo config plugin: release APK ni o'z kalitimiz bilan imzolash (android/ CNG — qo'lda o'zgartirish
 * `expo prebuild` da yo'qoladi, shuning uchun shu yerda).
 * Kalit: apps/mobile/credentials/release.properties + release.keystore (scripts/create-keystore.py; git ga kirmaydi).
 * Fayl bo'lmasa — Expo sukuti (debug kalit) qoladi, build buzilmaydi.
 */
const { withAppBuildGradle } = require("expo/config-plugins");

const MARK = "// mezon-release-signing";

const LOADER = `${MARK}
def mezonSigningFile = rootProject.file("../credentials/release.properties")
def mezonSigning = new Properties()
if (mezonSigningFile.exists()) { mezonSigningFile.withInputStream { mezonSigning.load(it) } }
`;

const CONFIG = `
        release {
            if (mezonSigningFile.exists()) {
                storeFile rootProject.file("../credentials/" + mezonSigning["storeFile"])
                storePassword mezonSigning["storePassword"]
                keyAlias mezonSigning["keyAlias"]
                keyPassword mezonSigning["keyPassword"]
            }
        }
    }
    buildTypes {`;

function apply(gradle) {
  if (gradle.includes(MARK)) return gradle;
  const signingEnd = /\n    }\n    buildTypes \{/;
  const releaseSigning = /(release \{[^}]*?)signingConfig signingConfigs\.debug/;
  if (!signingEnd.test(gradle) || !releaseSigning.test(gradle)) {
    throw new Error("withReleaseSigning: build.gradle tuzilmasi kutilganidek emas (Expo shabloni o'zgargan?)");
  }
  return (
    LOADER +
    gradle
      .replace(signingEnd, CONFIG)
      .replace(releaseSigning, "$1signingConfig mezonSigningFile.exists() ? signingConfigs.release : signingConfigs.debug")
  );
}

module.exports = (config) =>
  withAppBuildGradle(config, (cfg) => {
    cfg.modResults.contents = apply(cfg.modResults.contents);
    return cfg;
  });
module.exports.apply = apply;
