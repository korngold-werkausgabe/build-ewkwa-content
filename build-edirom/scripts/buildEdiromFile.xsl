<?xml version="1.0" encoding="UTF-8"?>
<!--
  Stylesheet: buildEdiromFile.xsl
  Purpose:
    Assemble the main EDIROM edition descriptor from a generic XML template and
    inject the project-specific metadata for the edition identifier, title, work
    list, and user preferences.

  Inputs:
    - A source EDIROM edition XML file.
    - Parameters: $editionId, $editionName, $editionPrefsPath, $editionWorksPath

  Output:
    - A normalized edition file that points to the generated work list and the
      preferences XML for the project.
-->
<xsl:stylesheet xmlns:edirom="http://www.edirom.de/ns/1.3" xmlns="http://www.edirom.de/ns/1.3" xmlns:xi="http://www.w3.org/2001/XInclude" xmlns:tei="http://www.tei-c.org/ns/1.0" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" exclude-result-prefixes="xs" version="1.0">

  <xsl:output indent="yes"/>

  <!-- Unique identifier of the edition project. -->
  <xsl:param name="editionId" select="''"/>
  <!-- Human-readable title displayed by the edition. -->
  <xsl:param name="editionName" select="''"/>
  <!-- Relative path used to resolve the edition preferences file. -->
  <xsl:param name="editionPrefsPath" select="''"/>
  <!-- Path to the generated works document included in the edition. -->
  <xsl:param name="editionWorksPath" select="''"/>

  <!-- Rewrite the root edition element and inject the edition identifier. -->
  <xsl:template match="edirom:edition">
    <edition xmlns="http://www.edirom.de/ns/1.3">
      <xsl:attribute name="xml:id">
        <xsl:value-of select="$editionId"/>
      </xsl:attribute>
      <xsl:apply-templates select="@*[name() != 'xml:id'] | node()"/>
    </edition>
  </xsl:template>

  <!-- Replace the edition name with the title supplied by the build configuration. -->
  <xsl:template match="edirom:editionName">
    <editionName>
      <xsl:value-of select="$editionName" />
    </editionName>
  </xsl:template>

  <!-- Embed the generated work list into the edition descriptor. -->
  <xsl:template match="edirom:works">
    <works>
      <xsl:copy-of select="document($editionWorksPath)/edirom:works/*"/>
    </works>
  </xsl:template>

  <!-- Point the edition configuration to the project preferences location. -->
  <xsl:template match="edirom:preferences">
    <preferences
      xlink:href="{concat('xmldb:exist:///db/apps/edirom-content/', $editionPrefsPath, '/prefs.xml')}"
    />
  </xsl:template>

  <!-- Default copy rule for all remaining nodes and attributes. -->
  <xsl:template match="@* | node()">
    <xsl:copy>
      <xsl:apply-templates select="@* | node()"/>
    </xsl:copy>
  </xsl:template>
</xsl:stylesheet>
