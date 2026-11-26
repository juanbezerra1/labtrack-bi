// labtrack-bi: query of the table Calendar (dim_date.csv).
// Power Query > New Source > Blank Query > Advanced Editor > paste this text. Name the query Calendar.
// Needs the DataFolder parameter first (see DataFolder.pq).
let
    Source = Csv.Document(File.Contents(Text.TrimEnd(DataFolder, "\") & "\dim_date.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Cleaned = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"date_key", "year", "quarter", "month_no", "year_month", "month_name", "month_start", "iso_weekday", "weekday_name", "is_weekend"}),
    Typed = Table.TransformColumnTypes(Cleaned, {{"date_key", type date}, {"year", Int64.Type}, {"quarter", Int64.Type}, {"month_no", Int64.Type}, {"year_month", type text}, {"month_name", type text}, {"month_start", type date}, {"iso_weekday", Int64.Type}, {"weekday_name", type text}, {"is_weekend", type logical}}, "en-US"),
    AddYearQuarter = Table.AddColumn(Typed, "Year-Quarter", each Text.From([year]) & " Q" & Text.From([quarter]), type text),
    Renamed = Table.RenameColumns(AddYearQuarter, {{"date_key", "Date"}, {"year", "Year"}, {"quarter", "Quarter"}, {"month_no", "Month No"}, {"year_month", "Year-Month"}, {"month_name", "Month"}, {"month_start", "Month Start"}, {"iso_weekday", "ISO Weekday"}, {"weekday_name", "Weekday"}, {"is_weekend", "Is Weekend"}}),
    Selected = Table.SelectColumns(Renamed, {"Date", "Year", "Quarter", "Year-Quarter", "Month No", "Year-Month", "Month", "Month Start", "ISO Weekday", "Weekday", "Is Weekend"})
in
    Selected
