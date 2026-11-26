// Checks the Power Query (M) of the model with Microsoft's own parser and language services:
// syntax, unknown names, duplicate names, and the number and type of the arguments of every call to a library function.
//
//   cd tools && npm ci && npm run check-m
//
// Prints one line per query and exits with 1 if any query has a diagnostic.
//
// The check of the TYPE of an argument is left out on purpose: with the library definitions of Microsoft it reports
// things like "expected text but got text" and "expected any but got null" on correct code, so it would hide the real
// findings. What is kept: syntax, unknown names, duplicate names, and the number of arguments of every library call.
"use strict";
const fs = require("fs");
const path = require("path");
const PQP = require("@microsoft/powerquery-parser");
const PQLS = require("@microsoft/powerquery-language-services");

async function main() {
    const [dir, libraryFile] = process.argv.slice(2);
    if (!dir || !libraryFile) {
        console.error("usage: node check_m.cjs <folder with .pq files> <m_library.json>");
        process.exit(2);
    }
    const symbols = JSON.parse(fs.readFileSync(libraryFile, "utf8"));
    const defs = PQLS.LibrarySymbolUtils.createLibraryDefinitions(symbols);
    if (!PQP.ResultUtils.isOk(defs)) {
        console.error("the library could not be read:", JSON.stringify(defs.error.failedLibrarySymbolConversions).slice(0, 400));
        process.exit(2);
    }
    const staticLibraryDefinitions = defs.value;
    const dynamicLibraryDefinitions = () => new Map();
    const library = {
        externalTypeResolver: PQLS.LibraryDefinitionUtils.externalTypeResolver({ staticLibraryDefinitions, dynamicLibraryDefinitions }),
        libraryDefinitions: { staticLibraryDefinitions, dynamicLibraryDefinitions },
    };
    const inspectionSettings = {
        ...PQP.DefaultSettings,
        isWorkspaceCacheAllowed: false,
        library,
        eachScopeById: undefined,
        typeStrategy: PQLS.TypeStrategy.Extended,
    };
    const analysisSettings = {
        inspectionSettings,
        isWorkspaceCacheAllowed: false,
        initialCorrelationId: undefined,
        traceManager: PQP.DefaultSettings.traceManager,
    };
    const validationSettings = PQLS.ValidationSettingsUtils.createValidationSettings(inspectionSettings, {
        cancellationToken: undefined,
        checkDiagnosticsOnParseError: false,
        checkForDuplicateIdentifiers: true,
        checkInvokeExpressions: true,
        checkUnknownIdentifiers: true,
        isWorkspaceCacheAllowed: false,
        library,
        source: "labtrack-bi",
    });

    let failed = 0;
    const files = fs.readdirSync(dir).filter((f) => f.endsWith(".pq")).sort();
    for (const file of files) {
        const body = fs.readFileSync(path.join(dir, file), "utf8");
        const name = file.replace(/\.pq$/, "");
        // A table query uses the parameter DataFolder, so the check defines it in front of the query.
        const text = name === "DataFolder" ? body : `let\n    DataFolder = "C:\\labtrack-bi\\data"\nin\n${body}`;
        const doc = PQLS.textDocument(`file:///${file}`, 1, text);
        const result = await PQLS.validate(doc, analysisSettings, validationSettings);
        let messages = [];
        if (!PQP.ResultUtils.isOk(result)) {
            messages = [`could not be validated: ${result.error.message}`];
        } else if (result.value) {
            messages = result.value.diagnostics
                .filter((d) => d.code !== "Error.InvokeArgumentTypeMismatch")
                .map((d) => `${d.range.start.line + 1}:${d.range.start.character + 1} ${d.message}`);
            if (result.value.hasSyntaxError) messages.unshift("syntax error");
        }
        console.log(`${messages.length === 0 ? "ok  " : "FAIL"} ${file}${messages.length ? "\n     " + messages.join("\n     ") : ""}`);
        if (messages.length) failed += 1;
    }
    console.log(`${files.length} queries checked, ${failed} with problems`);
    process.exit(failed ? 1 : 0);
}

main().catch((e) => {
    console.error(e);
    process.exit(2);
});
