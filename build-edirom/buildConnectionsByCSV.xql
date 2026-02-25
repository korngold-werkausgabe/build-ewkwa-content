xquery version "3.1";

declare namespace mei = "http://www.music-encoding.org/ns/mei";
declare namespace tei = "http://www.tei-c.org/ns/1.0";
declare namespace map = "http://www.w3.org/2005/xpath-functions/map";

(: ####################################### :)
(: External Parameters :)

declare variable $propertiesPath as xs:string external;
declare variable $csvPathsString as xs:string external;
declare variable $sourcesPath as xs:string external;
declare variable $editionHandle as xs:string external;
declare variable $subGroups as xs:string external;
declare variable $groupTitles as xs:string external;

(: ####################################### :)

declare function local:buildConnection($editionMeasure, $csvHead, $fields, $sources, $editionBaseURI) {
  <connection
    xmlns="http://www.edirom.de/ns/1.3"
    name="{$editionMeasure}"
    plist="{
        for $key at $pos in $csvHead
        let $value := $fields[$pos]
        (: sources :)
        let $sourceDoc := $sources[descendant::mei:identifier[@type = 'siglum' and text() = $key]]
        let $sourceFileName := tokenize(base-uri($sourceDoc), '/')[last()]
        let $source := $sourceDoc/mei:mei
        let $mdivN := tokenize($value, '_')[1]
        let $measureLabel :=
        if (contains($value, ';')) then
          (
          for $entry in tokenize($value, ';')
          return
            tokenize($entry, '_')[2]
          )
        else
          (
          tokenize($value, "_")[2]
          )
        
        return
          if (not(empty($measureLabel))) then
            (
            if (count($measureLabel) > 1) then
              (
              for $label in $measureLabel
              let $measureID := $source//mei:mdiv[@n = $mdivN]//mei:measure[@label = $label]/@xml:id
                where exists($measureID)
              return
                if (count($measureID) > 1) then
                  (
                  for $measure in $measureID
                  return
                    $editionBaseURI || $sourceFileName || '.xml#' || $measure || ' '
                  )
                else
                  (
                  $editionBaseURI || $sourceFileName || '.xml#' || $measureID || ' '
                  )
              )
            else
              (
              if (exists($source//mei:mdiv[@n = $mdivN]//mei:measure[@label = $measureLabel]/@xml:id)) then
                (
                let $measureID := $source//mei:mdiv[@n = $mdivN]//mei:measure[@label = $measureLabel]/@xml:id
                let $uri := if (count($measureID) > 1) then
                  (
                  for $measure in $measureID
                  return
                    $editionBaseURI || $sourceFileName || '.xml#' || $measure || ' '
                  )
                else
                  (
                  $editionBaseURI || $sourceFileName || '.xml#' || $measureID || ' '
                  )
                return
                  $uri
                )
              else
                ()
              )
            )
          else
            ()
      
      }"/>
};

(: Helper function to find and load the correct CSV for a given mdiv number :)
declare function local:getCsvForMdiv($mdivN as xs:string, $csvPaths as xs:string*) as xs:string? {
  let $matching := $csvPaths[contains(., '-' || $mdivN || '_')]
  return
    if ($matching) then 
      text { $matching[1] }
    else 
      ()
};

(: ####################################### :)
(: Variables :)

let $properties-file := try {
  doc($propertiesPath)
} catch * {
  error(
  xs:QName('local:csv-error'),
  'Properties file could not be loaded from "' || $propertiesPath || '". Error: ' || $err:code || ' - ' || $err:description
  )
}
let $properties := $properties-file//property
let $uuids := $properties-file//uuid

(:  ID of Edirom edition file. :)
let $editionID := $uuids[@name = 'edition']
(:  ID of MEI work file. :)
let $workID := $uuids[@name = 'work']

(: Parse multiple CSV paths from semicolon-separated string :)
let $csvPaths := if ($csvPathsString != '') then tokenize($csvPathsString, ';') else ()
let $sources := collection($sourcesPath)

let $editionHandle := if ($editionHandle != '') then $editionHandle else $properties[@name = 'editionHandle']/text()
let $editionBaseURI := 'xmldb:exist:///db/apps/edirom-content/' || $editionHandle || '/sources/'

(: ####################################### :)
return
  <concordance
    xmlns="http://www.edirom.de/ns/1.3"
    name='concMain'>
    <names>
      <name
        xml:lang='de'>Edition</name>
      <name
        xml:lang='en'>Edition</name>
    </names>
    <groups>
      <names>
        <name
          xml:lang='de'>{$groupTitles/title[xml:lang="de"]}</name>
        <name
          xml:lang='en'>{$groupTitles/title[xml:lang="en"]}</name>
      </names>
      {
        for $group in $subGroups
        return
          <group
            n='{$group/num/text()}'>
            <names>
              <name
                xml:lang='de'>{$group/title[@type='main' and xml:lang='de']} – {$group/*:title[@type='sub' and xml:lang='de']}</name>
              <name
                xml:lang='en'>{$group/title[@type='main' and xml:lang='en']} – {$group/*:title[@type='sub' and xml:lang='en']}</name>
            </names>
            <connections>{
                (: If the CSV file exists use csv mode :)
                try {
                  (: CSV handeling :)
                  let $csvText := fn:unparsed-text($inputCSV)
                  let $csvLines := tokenize($csvText, '\n')
                  let $csvHead := tokenize($csvLines[1], ',')
                  let $csvBody := remove($csvLines, 1)
                  
                  for $line in $csvBody
                  let $fields := tokenize($line, ',')
                  
                  let $mdivN := tokenize($fields[1], '_')[1]
                  let $editionMeasure := tokenize($fields[1], '_')[2]
                  return
                    if ($mdivN = $mdiv/@n) then
                      (local:buildConnection($editionMeasure, $csvHead, $fields, $sources, $editionBaseURI))
                    else
                      ()
                }
                catch * {
                  error(
                  xs:QName('local:csv-error'),
                  'CSV file could not be loaded from "' || $inputCSV || '". Error: ' || $err:code || ' - ' || $err:description
                  )
                }
              }
            </connections>
          </group>
      }
    </groups>
  </concordance>