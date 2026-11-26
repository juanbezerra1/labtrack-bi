// labtrack-bi: query of the table Device (dim_device.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Device.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\dim_device.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Cleaned = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"device_key", "kind", "model", "serial_no", "home_room", "acquired_on", "retired_on"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"device_key", Int64.Type}, {"kind", type text}, {"model", type text}, {"serial_no", type text}, {"home_room", type text}, {"acquired_on", type date}, {"retired_on", type date}}, "en-US"),
    Labelled = Table.TransformColumns(Typed, {{"kind", each if _ = null then null else Record.FieldOrDefault([dynamometer = "Dynamometer", eeg_amplifier = "EEG amplifier", emg_amplifier = "EMG amplifier", stimulator = "Stimulator"], _, _), type text}}),
    Renamed = Table.RenameColumns(Labelled, {{"device_key", "Device Key"}, {"kind", "Kind"}, {"model", "Model"}, {"serial_no", "Serial No"}, {"home_room", "Home Room"}, {"acquired_on", "Acquired On"}, {"retired_on", "Retired On"}}),
    Selected = Table.SelectColumns(Renamed, {"Device Key", "Kind", "Model", "Serial No", "Home Room", "Acquired On", "Retired On"})
in
    Selected
